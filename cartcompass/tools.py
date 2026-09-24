"""Tool Implementations and OpenAPI/JSON-Schema Declarations for UK Grocery & Online Optimization (GBP £)."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from cartcompass.models import (
    GeoCoordinate,
    GroceryStore,
    LoyaltyAdvantageAnalysis,
    LoyaltyProgramSpec,
    LoyaltyRecommendationTier,
    MatchedLineItem,
    ShoppingItemInput,
    SplitBasketOption,
    SplitStoreAllocation,
    StoreBasketQuote,
)


# ---------------------------------------------------------------------------
# 1. Explicit Tool & Interface Schema Registry (OpenAPI / Function Calling)
# ---------------------------------------------------------------------------
TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "resolve_uk_postcode",
        "description": (
            "Resolves a UK postcode (e.g., 'PO20 3SJ' Eastergate, 'RH12 1HQ' Horsham, "
            "'BN1 4GQ' Brighton, 'PO19 1RD' Chichester, 'SW1A 1AA' London) to exact "
            "latitude/longitude coordinates to reset the user's home location and "
            "trigger a fresh 20.0 km radius supermarket search."
        ),
        "parameters": {
            "type": "object",
            "required": ["postcode"],
            "properties": {
                "postcode": {
                    "type": "string",
                    "description": "UK Postcode or outward code (e.g. 'PO20 3SJ', 'RH12 1HQ', 'BN1 4GQ').",
                },
            },
        },
    },
    {
        "name": "parse_pasted_grocery_list",
        "description": (
            "Parses a free-form pasted grocery shopping list (multi-line or "
            "comma-separated text such as '2x Semi-Skimmed Milk 2L\\n1.5kg Chicken Breast') "
            "into structured ShoppingItemInput records."
        ),
        "parameters": {
            "type": "object",
            "required": ["raw_text"],
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "Free-text grocery list pasted by the user.",
                },
            },
        },
    },
    {
        "name": "discover_stores_within_radius",
        "description": (
            "Discovers all partner UK supermarkets within a strict geospatial "
            "radius (default 20.0 km) of the user's home in Eastergate, West Sussex, UK "
            "(Tesco, Sainsbury's, Lidl, Costco, Waitrose) PLUS UK Online Delivery "
            "Retailers (Amazon, Grape Tree, Whole Food Earth) that deliver to Eastergate."
        ),
        "parameters": {
            "type": "object",
            "required": ["latitude", "longitude", "radius_km"],
            "properties": {
                "latitude": {
                    "type": "number",
                    "minimum": -90,
                    "maximum": 90,
                    "description": "User location latitude (default 50.845561 for Eastergate, West Sussex).",
                },
                "longitude": {
                    "type": "number",
                    "minimum": -180,
                    "maximum": 180,
                    "description": "User location longitude (default -0.643677 for Eastergate, West Sussex).",
                },
                "radius_km": {
                    "type": "number",
                    "default": 20.0,
                    "exclusiveMinimum": 0,
                    "maximum": 100.0,
                    "description": "Maximum search radius in kilometers (default 20.0 km).",
                },
                "include_online_shops": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include online shops (Amazon, Grape Tree, Whole Food Earth).",
                },
            },
        },
    },
    {
        "name": "fetch_store_catalog_quote",
        "description": (
            "Queries a specific UK supermarket or online retailer's inventory, "
            "regular prices (GBP £), and loyalty/subscribe member prices for a "
            "list of normalized shopping items."
        ),
        "parameters": {
            "type": "object",
            "required": ["store_id", "items"],
            "properties": {
                "store_id": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["name", "quantity", "unit"],
                        "properties": {
                            "name": {"type": "string"},
                            "quantity": {"type": "number", "exclusiveMinimum": 0},
                            "unit": {"type": "string"},
                            "allow_substitutions": {"type": "boolean"},
                        },
                    },
                },
            },
        },
    },
    {
        "name": "analyze_loyalty_advantage",
        "description": (
            "Evaluates whether holding or joining a store's loyalty or online subscription "
            "scheme (Tesco Clubcard, Sainsbury's Nectar, Lidl Plus, Costco Membership, "
            "Amazon Prime/Subscribe & Save, Grape Tree Loyalty, Whole Food Earth Eco-Rewards) "
            "is financially advantageous in GBP (£)."
        ),
        "parameters": {
            "type": "object",
            "required": [
                "store_id",
                "regular_subtotal",
                "loyalty_subtotal",
                "user_active_programs",
            ],
            "properties": {
                "store_id": {"type": "string"},
                "regular_subtotal": {"type": "number"},
                "loyalty_subtotal": {"type": "number"},
                "user_active_programs": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "trips_per_year": {"type": "integer", "default": 52},
            },
        },
    },
    {
        "name": "optimize_split_basket_strategy",
        "description": (
            "Computes the optimal 2-store split-basket allocation in GBP (£) — including "
            "Hybrid Physical 20km Supermarket + Online Delivery (Amazon, Grape Tree, "
            "Whole Food Earth) combinations with zero extra driving detour — and compares "
            "against the best single-store option."
        ),
        "parameters": {
            "type": "object",
            "required": ["store_quotes", "user_location", "fuel_cost_per_km"],
            "properties": {
                "store_quotes": {"type": "array"},
                "user_location": {"type": "object"},
                "fuel_cost_per_km": {"type": "number"},
            },
        },
    },
]


# ---------------------------------------------------------------------------
# 1b. Free-Text / Bulk Pasted Grocery List Parser
# ---------------------------------------------------------------------------
_LEADING_QTY_UNIT_RE = re.compile(
    r"^(?P<qty>\d+(?:\.\d+)?)\s*(?:x|\*)?\s*"
    r"(?P<unit>kg|g|grams?|l|ml|litres?|liters?|loaves|loaf|dozen|packs?|pk|bottles?|tins?|cans?|bags?|count|ct)?\b\s*(?:of\s+)?(?P<name>.+)$",
    re.IGNORECASE,
)
_TRAILING_QTY_UNIT_RE = re.compile(
    r"^(?P<name>.+?)\s*[\(\-\:]\s*(?P<qty>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>kg|g|l|ml|loaf|dozen|packs?|pk|bags?|count|ct)[\)]?$",
    re.IGNORECASE,
)


def _canonicalize_unit(raw_unit: str | None, item_name: str) -> str:
  if raw_unit:
    u = raw_unit.strip().lower()
    if u in ("kg", "kilo", "kilos"):
      return "kg"
    if u in ("g", "gram", "grams"):
      return "g"
    if u in ("l", "litre", "litres", "liter", "liters"):
      return "l"
    if u in ("ml",):
      return "ml"
    if u in ("loaf", "loaves"):
      return "loaf"
    if u in ("dozen",):
      return "dozen"
    if u in ("pack", "packs", "pk", "bottle", "bottles", "tin", "tins", "can", "cans", "bag", "bags"):
      return "pack"
  low_name = item_name.lower()
  if any(w in low_name for w in ("chicken", "salmon", "beef", "apple", "potato", "mince")):
    return "kg"
  if any(w in low_name for w in ("bread", "sourdough", "bloomer")):
    return "loaf"
  if "egg" in low_name:
    return "dozen"
  if "olive oil" in low_name:
    return "l"
  if any(w in low_name for w in ("pasta", "coffee", "yogurt", "spinach", "cheddar", "cheese", "almond", "walnut", "oat", "lentil", "seed")):
    return "pack"
  return "count"


def parse_pasted_grocery_list(raw_text: str) -> list[ShoppingItemInput]:
  """Parses a multi-line or comma-separated pasted shopping list into structured items."""
  if not raw_text or not raw_text.strip():
    return []

  raw_lines = [
      line.strip()
      for line in re.split(r"[\r\n;]+", raw_text.strip())
      if line.strip()
  ]
  if len(raw_lines) == 1 and "," in raw_lines[0]:
    raw_lines = [seg.strip() for seg in raw_lines[0].split(",") if seg.strip()]

  parsed_items: list[ShoppingItemInput] = []
  for line in raw_lines:
    if line.count(":") == 2:
      parts = [p.strip() for p in line.split(":")]
      try:
        parsed_items.append(
            ShoppingItemInput(
                name=parts[0],
                quantity=float(parts[1]),
                unit=parts[2] or "count",
            )
        )
        continue
      except ValueError:
        pass

    cleaned = re.sub(r"^[\s\-\*\u2022]+", "", line).strip()
    if not cleaned:
      continue

    m_lead = _LEADING_QTY_UNIT_RE.match(cleaned)
    if m_lead and m_lead.group("name").strip():
      qty = float(m_lead.group("qty"))
      raw_u = m_lead.group("unit")
      name = m_lead.group("name").strip()
      unit = _canonicalize_unit(raw_u, name)
      parsed_items.append(ShoppingItemInput(name=name, quantity=qty, unit=unit))
      continue

    m_trail = _TRAILING_QTY_UNIT_RE.match(cleaned)
    if m_trail and m_trail.group("name").strip():
      qty = float(m_trail.group("qty"))
      raw_u = m_trail.group("unit")
      name = m_trail.group("name").strip()
      unit = _canonicalize_unit(raw_u, name)
      parsed_items.append(ShoppingItemInput(name=name, quantity=qty, unit=unit))
      continue

    unit = _canonicalize_unit(None, cleaned)
    parsed_items.append(ShoppingItemInput(name=cleaned, quantity=1.0, unit=unit))

  return parsed_items


# ---------------------------------------------------------------------------
# 2. UK Postcode Resolver & Geospatial 20km + Online Store Network
# ---------------------------------------------------------------------------
UK_POSTCODE_DIRECTORY: dict[str, tuple[float, float, str, str]] = {
    "PO20 3SJ": (50.845561, -0.643677, "Home (Eastergate, West Sussex, UK)", "Eastergate / Barnham"),
    "PO20": (50.845561, -0.643677, "Home (Eastergate, West Sussex, UK)", "Eastergate / Barnham"),
    "PO19 1RD": (50.836500, -0.779200, "Chichester, West Sussex, UK (PO19 1RD)", "Chichester"),
    "PO19": (50.836500, -0.779200, "Chichester, West Sussex, UK (PO19)", "Chichester"),
    "PO21 1BA": (50.782800, -0.674600, "Bognor Regis, West Sussex, UK (PO21 1BA)", "Bognor Regis"),
    "PO21": (50.782800, -0.674600, "Bognor Regis, West Sussex, UK (PO21)", "Bognor Regis"),
    "PO22 9ND": (50.814120, -0.694894, "North Bersted / Bognor Regis, West Sussex (PO22 9ND)", "Bognor Regis"),
    "PO22": (50.814120, -0.694894, "Bognor Regis North, West Sussex (PO22)", "Bognor Regis"),
    "BN18 9AB": (50.854400, -0.556200, "Arundel, West Sussex, UK (BN18 9AB)", "Arundel / Littlehampton"),
    "BN18": (50.854400, -0.556200, "Arundel, West Sussex, UK (BN18)", "Arundel / Littlehampton"),
    "BN11 1HQ": (50.814700, -0.371400, "Worthing, West Sussex, UK (BN11 1HQ)", "Worthing"),
    "BN11": (50.814700, -0.371400, "Worthing, West Sussex, UK (BN11)", "Worthing"),
    "RH12 1HQ": (51.063200, -0.326200, "Horsham Town Centre, West Sussex, UK (RH12 1HQ)", "Horsham"),
    "RH12": (51.063200, -0.326200, "Horsham, West Sussex, UK (RH12)", "Horsham"),
    "BN1 4GQ": (50.822500, -0.137200, "Brighton, East Sussex, UK (BN1 4GQ)", "Brighton & Hove"),
    "BN1": (50.822500, -0.137200, "Brighton, East Sussex, UK (BN1)", "Brighton & Hove"),
    "GU28 0BG": (50.986900, -0.610500, "Petworth, West Sussex, UK (GU28 0BG)", "Petworth / Midhurst"),
    "GU28": (50.986900, -0.610500, "Petworth, West Sussex, UK (GU28)", "Petworth / Midhurst"),
    "PO9 1ND": (50.851700, -0.983200, "Havant, Hampshire, UK (PO9 1ND)", "Havant / Portsmouth"),
    "PO9": (50.851700, -0.983200, "Havant, Hampshire, UK (PO9)", "Havant / Portsmouth"),
    "SO14 7DW": (50.909700, -1.404400, "Southampton, Hampshire, UK (SO14 7DW)", "Southampton"),
    "SO14": (50.909700, -1.404400, "Southampton, Hampshire, UK (SO14)", "Southampton"),
    "SW1A 1AA": (51.501400, -0.141900, "Westminster, Central London, UK (SW1A 1AA)", "Central London"),
    "SW1A": (51.501400, -0.141900, "Westminster, Central London, UK (SW1A)", "Central London"),
    "M1 1AG": (53.480800, -2.242600, "Manchester City Centre, UK (M1 1AG)", "Manchester"),
    "M1": (53.480800, -2.242600, "Manchester City Centre, UK (M1)", "Manchester"),
    "B1 1BB": (52.486200, -1.890400, "Birmingham City Centre, UK (B1 1BB)", "Birmingham"),
    "B1": (52.486200, -1.890400, "Birmingham City Centre, UK (B1)", "Birmingham"),
    "EH1 1YZ": (55.953300, -3.188300, "Edinburgh City Centre, Scotland, UK (EH1 1YZ)", "Edinburgh"),
    "EH1": (55.953300, -3.188300, "Edinburgh City Centre, Scotland, UK (EH1)", "Edinburgh"),
}


def resolve_uk_postcode(postcode: str) -> GeoCoordinate:
  """Resolves a UK postcode or outward code to a GeoCoordinate to reset a 20km search."""
  cleaned = re.sub(r"\s+", " ", postcode.strip().upper())
  if not cleaned:
    return GeoCoordinate(
        latitude=50.845561,
        longitude=-0.643677,
        label="Home (Eastergate, West Sussex, UK)",
        postcode="PO20 3SJ",
    )

  # Format standard UK postcode spacing (e.g., PO203SJ -> PO20 3SJ)
  compact = cleaned.replace(" ", "")
  if len(compact) >= 5 and re.match(r"^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$", compact):
    formatted = f"{compact[:-3]} {compact[-3:]}"
  else:
    formatted = cleaned

  outward = formatted.split(" ")[0]

  if formatted in UK_POSTCODE_DIRECTORY:
    lat, lon, label, _ = UK_POSTCODE_DIRECTORY[formatted]
    return GeoCoordinate(latitude=lat, longitude=lon, label=label, postcode=formatted)

  if outward in UK_POSTCODE_DIRECTORY:
    lat, lon, base_label, town = UK_POSTCODE_DIRECTORY[outward]
    # Add subtle deterministic offset if full postcode differs from outward anchor
    if formatted != outward:
      digest = int(hashlib.sha256(formatted.encode("utf-8")).hexdigest()[:6], 16)
      d_lat = ((digest % 40) - 20) * 0.0004
      d_lon = (((digest >> 6) % 40) - 20) * 0.0005
      lat = round(lat + d_lat, 6)
      lon = round(lon + d_lon, 6)
    return GeoCoordinate(
        latitude=lat,
        longitude=lon,
        label=f"{town}, UK ({formatted})",
        postcode=formatted,
    )

  # Deterministic fallback for any other UK postcode prefix
  digest = int(hashlib.sha256(formatted.encode("utf-8")).hexdigest()[:8], 16)
  lat = round(50.80 + (digest % 350) / 100.0, 6)
  lon = round(-2.40 + ((digest >> 8) % 260) / 100.0, 6)
  return GeoCoordinate(
      latitude=lat,
      longitude=lon,
      label=f"UK Postcode Area {formatted}",
      postcode=formatted,
  )


def haversine_distance_km(coord1: GeoCoordinate, coord2: GeoCoordinate) -> float:
  """Calculates great-circle distance in kilometers between two coordinates."""
  coord1.validate()
  coord2.validate()
  earth_radius_km = 6371.0088
  lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
  lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)
  dlat = lat2 - lat1
  dlon = lon2 - lon1
  a = (
      math.sin(dlat / 2.0) ** 2
      + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
  )
  c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
  return round(earth_radius_km * c, 2)


def _extract_area_town(anchor: GeoCoordinate) -> tuple[str, str]:
  """Extracts a human-readable town/district and postcode for store naming."""
  pc = getattr(anchor, "postcode", "") or "PO20 3SJ"
  outward = pc.split(" ")[0].upper()
  if outward in UK_POSTCODE_DIRECTORY:
    _, _, _, town = UK_POSTCODE_DIRECTORY[outward]
    return town, pc
  if "Eastergate" in anchor.label or (
      abs(anchor.latitude - 50.845561) < 0.05
      and abs(anchor.longitude - (-0.643677)) < 0.05
  ):
    return "Eastergate / Bognor / Chichester", "PO20 3SJ"
  cleaned_label = anchor.label.split("(")[0].strip().rstrip(",")
  return cleaned_label or "Local District", pc


def _build_regional_store_network(
    anchor: GeoCoordinate, include_online_shops: bool = True
) -> list[GroceryStore]:
  """Builds the UK grocery network around the user's active postcode/coordinates (20km) plus Online Shops."""
  cos_lat = max(0.2, math.cos(math.radians(anchor.latitude)))
  town, postcode_str = _extract_area_town(anchor)
  is_eastergate_area = "Eastergate" in town or postcode_str.startswith(("PO20", "PO19", "PO21", "PO22"))

  def offset_coord(km_north: float, km_east: float, label: str) -> GeoCoordinate:
    d_lat = km_north / 111.32
    d_lon = km_east / (111.32 * cos_lat)
    return GeoCoordinate(
        latitude=round(anchor.latitude + d_lat, 6),
        longitude=round(anchor.longitude + d_lon, 6),
        label=label,
        postcode=postcode_str,
    )

  sainsburys_name = (
      "Sainsbury's Bognor Regis Superstore"
      if is_eastergate_area
      else f"Sainsbury's {town} Superstore"
  )
  tesco_name = (
      "Tesco Extra Bognor / Chichester"
      if is_eastergate_area
      else f"Tesco Extra {town}"
  )
  lidl_name = (
      "Lidl Chichester Portfield"
      if is_eastergate_area
      else f"Lidl {town} Retail Park"
  )
  waitrose_name = (
      "Waitrose & Partners Chichester"
      if is_eastergate_area
      else f"Waitrose & Partners {town}"
  )
  costco_name = (
      "Costco Wholesale South Coast (A27 Corridor)"
      if is_eastergate_area
      else f"Costco Wholesale {town} Regional Warehouse"
  )
  excluded_1_name = (
      "Tesco Extra Horsham (North Sussex >20km)"
      if is_eastergate_area
      else f"Tesco Extra Regional North (>20km from {postcode_str})"
  )
  excluded_2_name = (
      "Waitrose & Partners Brighton (>20km)"
      if is_eastergate_area
      else f"Waitrose & Partners Regional East (>20km from {postcode_str})"
  )

  stores: list[GroceryStore] = [
      GroceryStore(
          store_id="STORE-SAINSBURYS-01",
          name=sainsburys_name,
          chain="Sainsbury's",
          coordinate=offset_coord(-3.8, -1.9, sainsburys_name),
          address=(
              "Shripney Road, Bognor Regis, West Sussex, PO22 9NF"
              if is_eastergate_area
              else f"High Street & Retail Way, {town}, {postcode_str}"
          ),
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-SAINSBURYS-NECTAR",
              program_name="Sainsbury's Nectar Card (Free)",
              annual_fee=0.0,
              signup_bonus_credit=2.50,
              points_cashback_rate=0.015,
              perks_summary="Free Nectar membership; instant Nectar Prices across hundreds of items + 1.5% Nectar points.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
      GroceryStore(
          store_id="STORE-TESCO-02",
          name=tesco_name,
          chain="Tesco",
          coordinate=offset_coord(-3.5, -3.6, tesco_name),
          address=(
              "Shripney Road, Bognor Regis, West Sussex, PO22 9ND"
              if is_eastergate_area
              else f"Extra Superstore Park, {town}, {postcode_str}"
          ),
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-TESCO-CLUBCARD",
              program_name="Tesco Clubcard (Free)",
              annual_fee=0.0,
              signup_bonus_credit=3.00,
              points_cashback_rate=0.015,
              perks_summary="Free Clubcard; exclusive yellow-label Clubcard Prices + 1.5% in Clubcard Reward Partner vouchers.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
      GroceryStore(
          store_id="STORE-LIDL-03",
          name=lidl_name,
          chain="Lidl",
          coordinate=offset_coord(-0.6, -7.7, lidl_name),
          address=(
              "Portfield Way, Chichester, West Sussex, PO19 7YH"
              if is_eastergate_area
              else f"Portfield & Ring Road Retail Park, {town}, {postcode_str}"
          ),
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-LIDL-PLUS",
              program_name="Lidl Plus App (Free)",
              annual_fee=0.0,
              signup_bonus_credit=5.00,
              points_cashback_rate=0.025,
              perks_summary="Free Lidl Plus app; 10-20% weekly digital coupons, free bakery treats & Coupon Plus spend rebates.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
      GroceryStore(
          store_id="STORE-WAITROSE-04",
          name=waitrose_name,
          chain="Waitrose",
          coordinate=offset_coord(-1.1, -8.5, waitrose_name),
          address=(
              "Via Ravenna, Chichester, West Sussex, PO19 1RD"
              if is_eastergate_area
              else f"Central Shopping Precinct, {town}, {postcode_str}"
          ),
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-WAITROSE-MY",
              program_name="myWaitrose (Free)",
              annual_fee=0.0,
              signup_bonus_credit=0.0,
              points_cashback_rate=0.01,
              perks_summary="Free myWaitrose membership; personalised weekly money-off vouchers & counter discounts.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
      GroceryStore(
          store_id="STORE-COSTCO-05",
          name=costco_name,
          chain="Costco",
          coordinate=offset_coord(1.8, -18.1, costco_name),
          address=(
              "A27 Retail & Trade Park, Havant/Chichester Corridor, PO9 1ND"
              if is_eastergate_area
              else f"Regional Trade & Wholesale Park ({town} 18km Corridor)"
          ),
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-COSTCO-GOLDSTAR",
              program_name="Costco UK Individual / Gold Star Membership",
              annual_fee=33.60,
              signup_bonus_credit=10.00,
              points_cashback_rate=0.02,
              perks_summary="£33.60/yr inc. VAT (£0.65/wk); Kirkland Signature & wholesale bulk pricing + 2% reward rebate.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
      # Two physical stores intentionally >20km from the active postcode to verify the strict 20km radius boundary:
      GroceryStore(
          store_id="STORE-TESCO-HORSHAM-06",
          name=excluded_1_name,
          chain="Tesco Extra Horsham",
          coordinate=offset_coord(24.2, 11.4, excluded_1_name),
          address="Wickhurst Lane, Broadbridge Heath, Horsham, RH12 3YU",
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-TESCO-CLUBCARD",
              program_name="Tesco Clubcard (Free)",
              annual_fee=0.0,
              signup_bonus_credit=0.0,
              points_cashback_rate=0.015,
              perks_summary="Free Clubcard tier.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
      GroceryStore(
          store_id="STORE-WAITROSE-BRIGHTON-07",
          name=excluded_2_name,
          chain="Waitrose Brighton",
          coordinate=offset_coord(-2.4, 31.6, excluded_2_name),
          address="130-134 Western Road, Brighton, BN1 2LA",
          loyalty_program=LoyaltyProgramSpec(
              program_id="LP-WAITROSE-MY",
              program_name="myWaitrose (Free)",
              annual_fee=0.0,
              signup_bonus_credit=0.0,
              points_cashback_rate=0.01,
              perks_summary="Free myWaitrose tier.",
          ),
          store_type="PHYSICAL_20KM",
          catalog_scope="FULL_SUPERMARKET",
      ),
  ]

  if include_online_shops:
    stores.extend([
        GroceryStore(
            store_id="STORE-ONLINE-AMAZON",
            name="Amazon UK (Ambient Pantry & Subscribe & Save)",
            chain="Amazon",
            coordinate=anchor,
            address=f"Online UK Parcel / Subscribe & Save Delivery to {postcode_str} (Ambient Pantry & Wholefoods Only)",
            loyalty_program=LoyaltyProgramSpec(
                program_id="LP-AMAZON-PRIME",
                program_name="Amazon Prime & Subscribe & Save (Up to 15% Off)",
                annual_fee=95.0,
                signup_bonus_credit=10.0,
                points_cashback_rate=0.02,
                perks_summary="£95/yr (£1.83/wk); 10-15% Subscribe & Save discounts on ambient pantry, coffee, oils, pasta & wholefoods.",
            ),
            distance_km=0.0,
            within_radius=True,
            estimated_drive_minutes=0.0,
            store_type="ONLINE_UK",
            standard_delivery_fee=3.99,
            free_delivery_threshold=40.0,
            catalog_scope="ONLINE_AMBIENT_PANTRY",
        ),
        GroceryStore(
            store_id="STORE-ONLINE-GRAPETREE",
            name="Grape Tree Health Foods (Online UK)",
            chain="Grape Tree",
            coordinate=anchor,
            address=f"Online Direct Delivery to {postcode_str} (Wholefoods, Nuts, Seeds, Dried Fruit, Oils & Grains Only — No Fresh/Chilled)",
            loyalty_program=LoyaltyProgramSpec(
                program_id="LP-GRAPETREE-LOYALTY",
                program_name="Grape Tree Tree-Mendous Loyalty Club (Free)",
                annual_fee=0.0,
                signup_bonus_credit=5.0,
                points_cashback_rate=0.03,
                perks_summary="Free online loyalty tier; up to 20% off bulk wholefoods, nuts, seeds, pasta & oils + 3% reward points.",
            ),
            distance_km=0.0,
            within_radius=True,
            estimated_drive_minutes=0.0,
            store_type="ONLINE_UK",
            standard_delivery_fee=3.50,
            free_delivery_threshold=35.0,
            catalog_scope="ONLINE_WHOLEFOOD_SPECIALIST",
        ),
        GroceryStore(
            store_id="STORE-ONLINE-WHOLEFOODEARTH",
            name="Whole Food Earth (Online Sustainable Wholefoods)",
            chain="Whole Food Earth",
            coordinate=anchor,
            address=f"Online Eco-Delivery to {postcode_str} (Organic Grains, Pulses, Nuts, Coffee & Pantry Only — No Fresh/Chilled)",
            loyalty_program=LoyaltyProgramSpec(
                program_id="LP-WHOLEFOODEARTH-REWARDS",
                program_name="Whole Food Earth Eco-Rewards Club (Free)",
                annual_fee=0.0,
                signup_bonus_credit=5.0,
                points_cashback_rate=0.035,
                perks_summary="Free Eco-Rewards membership; 12-18% bulk pantry & organic wholefood discounts + 3.5% Eco-Points.",
            ),
            distance_km=0.0,
            within_radius=True,
            estimated_drive_minutes=0.0,
            store_type="ONLINE_UK",
            standard_delivery_fee=2.99,
            free_delivery_threshold=30.0,
            catalog_scope="ONLINE_WHOLEFOOD_SPECIALIST",
        ),
    ])

  return stores


def discover_stores_within_radius(
    user_location: GeoCoordinate,
    radius_km: float = 20.0,
    include_online_shops: bool = True,
) -> tuple[list[GroceryStore], list[GroceryStore]]:
  """Returns (stores_within_radius_or_online, stores_excluded_outside_radius)."""
  if radius_km <= 0:
    raise ValueError(f"radius_km must be positive, got {radius_km}")

  all_stores = _build_regional_store_network(
      user_location, include_online_shops=include_online_shops
  )
  included: list[GroceryStore] = []
  excluded: list[GroceryStore] = []

  for store in all_stores:
    if store.store_type == "ONLINE_UK":
      store.distance_km = 0.0
      store.estimated_drive_minutes = 0.0
      store.within_radius = True
      included.append(store)
      continue

    dist = haversine_distance_km(user_location, store.coordinate)
    store.distance_km = dist
    store.estimated_drive_minutes = round(dist * 1.55 + 3.0, 1)
    if dist <= radius_km:
      store.within_radius = True
      included.append(store)
    else:
      store.within_radius = False
      excluded.append(store)

  included.sort(key=lambda s: (1 if s.store_type == "ONLINE_UK" else 0, s.distance_km))
  excluded.sort(key=lambda s: s.distance_km)
  return included, excluded


# ---------------------------------------------------------------------------
# 3. UK Supermarket & Online Catalog Pricing & Fulfilment Validity (GBP £)
# ---------------------------------------------------------------------------
CANONICAL_CATALOG: list[dict[str, Any]] = [
    {
        "sku_id": "SKU-MILK-2L",
        "item_category": "FRESH_CHILLED",
        "keywords": ["milk", "semi-skimmed milk", "whole milk", "skimmed milk", "4 pints milk"],
        "product_name": "British Semi-Skimmed Milk (2.27L / 4 Pints)",
        "canonical_unit": "count",
        "prices": {
            "STORE-SAINSBURYS-01": (1.65, 1.45, "Nectar Price -£0.20"),
            "STORE-TESCO-02": (1.65, 1.45, "Clubcard Price -£0.20"),
            "STORE-LIDL-03": (1.45, 1.35, "Lidl Plus Dairy Coupon"),
            "STORE-WAITROSE-04": (1.85, 1.75, "myWaitrose Essential"),
            "STORE-COSTCO-05": (1.40, 1.18, "Costco Twin-Jug Member Rate"),
        },
    },
    {
        "sku_id": "SKU-EGGS-12",
        "item_category": "FRESH_CHILLED",
        "keywords": ["eggs", "egg", "dozen eggs", "free range eggs", "large eggs", "12 eggs"],
        "product_name": "British Free-Range Large Eggs (12 Pack)",
        "canonical_unit": "dozen",
        "prices": {
            "STORE-SAINSBURYS-01": (3.25, 2.75, "Nectar Price Save £0.50"),
            "STORE-TESCO-02": (3.20, 2.70, "Clubcard Price Save £0.50"),
            "STORE-LIDL-03": (2.69, 2.39, "Lidl Plus Weekly Offer"),
            "STORE-WAITROSE-04": (3.85, 3.50, "Duchy Free-Range Promo"),
            "STORE-COSTCO-05": (2.65, 2.15, "Kirkland 24-Tray Member Split"),
        },
    },
    {
        "sku_id": "SKU-BREAD-LOAF",
        "item_category": "FRESH_CHILLED",
        "keywords": ["bread", "sourdough", "loaf", "bloomer", "wholemeal bread", "toast"],
        "product_name": "Artisan White Sourdough Bloomer (800g)",
        "canonical_unit": "loaf",
        "prices": {
            "STORE-SAINSBURYS-01": (2.30, 1.90, "Nectar Bakery Special"),
            "STORE-TESCO-02": (2.25, 1.85, "Clubcard Finest Bakery"),
            "STORE-LIDL-03": (1.79, 1.49, "Lidl Plus In-Store Bakery -£0.30"),
            "STORE-WAITROSE-04": (2.75, 2.50, "No.1 Sourdough Offer"),
            "STORE-COSTCO-05": (2.10, 1.65, "Kirkland Artisan Twin Loaf Rate"),
        },
    },
    {
        "sku_id": "SKU-CHICKEN-KG",
        "item_category": "FRESH_CHILLED",
        "keywords": ["chicken", "chicken breast", "poultry", "chicken thighs", "chicken fillets"],
        "product_name": "British Chicken Breast Fillets (1kg)",
        "canonical_unit": "kg",
        "prices": {
            "STORE-SAINSBURYS-01": (7.20, 6.25, "Nectar Butcher Price"),
            "STORE-TESCO-02": (7.10, 6.10, "Clubcard Family Pack Price"),
            "STORE-LIDL-03": (6.49, 5.79, "Lidl Plus Birchwood Offer"),
            "STORE-WAITROSE-04": (9.20, 8.25, "Higher Welfare British Poultry"),
            "STORE-COSTCO-05": (6.20, 5.15, "Costco Wholesale Butcher Pack"),
        },
    },
    {
        "sku_id": "SKU-APPLES-KG",
        "item_category": "FRESH_CHILLED",
        "keywords": ["apple", "apples", "braeburn", "gala apples", "honeycrisp", "fruit"],
        "product_name": "Sussex Braeburn & Gala Apples (1kg)",
        "canonical_unit": "kg",
        "prices": {
            "STORE-SAINSBURYS-01": (2.50, 2.10, "Nectar British Orchard Deal"),
            "STORE-TESCO-02": (2.45, 2.00, "Clubcard Fresh 5-a-Day"),
            "STORE-LIDL-03": (1.99, 1.69, "Lidl Plus Pick of the Week"),
            "STORE-WAITROSE-04": (2.95, 2.65, "Sussex Grower Select"),
            "STORE-COSTCO-05": (2.20, 1.75, "Costco 2kg Crate Member Rate"),
        },
    },
    {
        "sku_id": "SKU-PASTA-PACK",
        "item_category": "AMBIENT_WHOLEFOOD",
        "keywords": ["pasta", "spaghetti", "penne", "fusilli", "macaroni", "noodles"],
        "product_name": "Italian Durum Wheat Penne Pasta (500g)",
        "canonical_unit": "pack",
        "prices": {
            "STORE-SAINSBURYS-01": (1.35, 1.00, "Nectar Cupboard Price"),
            "STORE-TESCO-02": (1.30, 0.95, "Clubcard Price £0.95"),
            "STORE-LIDL-03": (0.89, 0.75, "Lidl Plus Italiamo Coupon"),
            "STORE-WAITROSE-04": (1.65, 1.45, "Essential Waitrose Pasta"),
            "STORE-COSTCO-05": (1.10, 0.82, "Garofalo Multipack Member Rate"),
            "STORE-ONLINE-AMAZON": (1.05, 0.68, "Amazon Subscribe & Save -15%"),
            "STORE-ONLINE-GRAPETREE": (0.99, 0.62, "Grape Tree Bulk Wholefood Pasta Deal"),
            "STORE-ONLINE-WHOLEFOODEARTH": (0.95, 0.59, "Whole Food Earth 2kg Bulk Split Rate"),
        },
    },
    {
        "sku_id": "SKU-COFFEE-PACK",
        "item_category": "AMBIENT_WHOLEFOOD",
        "keywords": ["coffee", "coffee beans", "espresso", "ground coffee", "roast coffee"],
        "product_name": "Rich Roast Arabica Ground Coffee (400g)",
        "canonical_unit": "pack",
        "prices": {
            "STORE-SAINSBURYS-01": (5.50, 4.25, "Nectar Price Save £1.25"),
            "STORE-TESCO-02": (5.40, 4.15, "Clubcard Price Save £1.25"),
            "STORE-LIDL-03": (3.99, 3.39, "Lidl Plus Bellarom Deal"),
            "STORE-WAITROSE-04": (6.25, 5.50, "myWaitrose Coffee Offer"),
            "STORE-COSTCO-05": (4.45, 3.45, "Kirkland Colombian Member Rate"),
            "STORE-ONLINE-AMAZON": (4.15, 2.75, "Amazon Subscribe & Save -15%"),
            "STORE-ONLINE-GRAPETREE": (3.95, 2.85, "Grape Tree Roaster Value Bag"),
            "STORE-ONLINE-WHOLEFOODEARTH": (3.85, 2.69, "Whole Food Earth Organic Arabica Bulk"),
        },
    },
    {
        "sku_id": "SKU-OLIVEOIL-L",
        "item_category": "AMBIENT_WHOLEFOOD",
        "keywords": ["olive oil", "extra virgin olive oil", "cooking oil", "evoo"],
        "product_name": "Extra Virgin Cold-Pressed Olive Oil (1L)",
        "canonical_unit": "l",
        "prices": {
            "STORE-SAINSBURYS-01": (8.25, 6.95, "Nectar Mediterranean Price"),
            "STORE-TESCO-02": (8.15, 6.80, "Clubcard Price Save £1.35"),
            "STORE-LIDL-03": (6.79, 5.99, "Lidl Plus Primadonna Offer"),
            "STORE-WAITROSE-04": (9.50, 8.50, "Estate Olive Oil Promo"),
            "STORE-COSTCO-05": (6.80, 5.40, "Kirkland Organic 2L Equivalent"),
            "STORE-ONLINE-AMAZON": (6.50, 4.85, "Amazon Subscribe & Save Deal"),
            "STORE-ONLINE-GRAPETREE": (5.95, 4.45, "Grape Tree Mediterranean Bulk Tin"),
            "STORE-ONLINE-WHOLEFOODEARTH": (5.85, 4.39, "Whole Food Earth Cold-Pressed Refill"),
        },
    },
    {
        "sku_id": "SKU-YOGURT-PACK",
        "item_category": "FRESH_CHILLED",
        "keywords": ["yogurt", "greek yogurt", "yoghurt", "natural yogurt", "skyr"],
        "product_name": "Authentic Greek Style Natural Yogurt (500g)",
        "canonical_unit": "pack",
        "prices": {
            "STORE-SAINSBURYS-01": (2.00, 1.60, "Nectar Fridge Price"),
            "STORE-TESCO-02": (1.95, 1.55, "Clubcard Chilled Saver"),
            "STORE-LIDL-03": (1.49, 1.25, "Lidl Plus Milbona Coupon"),
            "STORE-WAITROSE-04": (2.40, 2.15, "Greek Strained Offer"),
            "STORE-COSTCO-05": (1.65, 1.30, "Fage Twin-Tub Member Rate"),
        },
    },
    {
        "sku_id": "SKU-SALMON-KG",
        "item_category": "FRESH_CHILLED",
        "keywords": ["salmon", "fish", "salmon fillets", "seafood", "trout", "scottish salmon"],
        "product_name": "Scottish Atlantic Salmon Fillets (1kg)",
        "canonical_unit": "kg",
        "prices": {
            "STORE-SAINSBURYS-01": (17.50, 14.80, "Nectar Fishmonger Special"),
            "STORE-TESCO-02": (17.20, 14.50, "Clubcard Finest Catch"),
            "STORE-LIDL-03": (14.99, 13.29, "Lidl Plus Strathvale Salmon"),
            "STORE-WAITROSE-04": (19.80, 17.50, "Responsibly Sourced Scottish"),
            "STORE-COSTCO-05": (15.20, 12.40, "Kirkland Whole Side Fillet Rate"),
        },
    },
    {
        "sku_id": "SKU-SPINACH-PACK",
        "item_category": "FRESH_CHILLED",
        "keywords": ["spinach", "baby spinach", "salad", "kale", "lettuce", "greens"],
        "product_name": "Triple-Washed Baby Spinach (250g)",
        "canonical_unit": "pack",
        "prices": {
            "STORE-SAINSBURYS-01": (1.70, 1.35, "Nectar Produce Price"),
            "STORE-TESCO-02": (1.65, 1.30, "Clubcard Salad Deal"),
            "STORE-LIDL-03": (1.29, 1.09, "Lidl Plus Oaklands Greens"),
            "STORE-WAITROSE-04": (2.00, 1.80, "Organic Washed Leaves"),
            "STORE-COSTCO-05": (1.45, 1.15, "Costco Catering Bag Split"),
        },
    },
    {
        "sku_id": "SKU-CHEDDAR-PACK",
        "item_category": "FRESH_CHILLED",
        "keywords": ["cheese", "cheddar", "cheddar cheese", "mature cheddar", "cathedral city"],
        "product_name": "Cathedral Vintage Mature Cheddar (400g)",
        "canonical_unit": "pack",
        "prices": {
            "STORE-SAINSBURYS-01": (3.95, 2.95, "Nectar Price Save £1.00"),
            "STORE-TESCO-02": (3.90, 2.90, "Clubcard Price £2.90"),
            "STORE-LIDL-03": (2.99, 2.49, "Lidl Plus Valley Spire Coupon"),
            "STORE-WAITROSE-04": (4.40, 3.90, "West Country Farmhouse Deal"),
            "STORE-COSTCO-05": (3.25, 2.45, "Costco 1kg Block Equivalent"),
        },
    },
    {
        "sku_id": "SKU-NUTS-SEEDS-PACK",
        "item_category": "AMBIENT_WHOLEFOOD",
        "keywords": ["almonds", "walnuts", "cashews", "nuts", "chia seeds", "pumpkin seeds", "oats", "lentils", "dried fruit", "wholefoods"],
        "product_name": "Raw Whole Almonds, Walnuts & Chia Seeds (500g)",
        "canonical_unit": "pack",
        "prices": {
            "STORE-SAINSBURYS-01": (5.90, 4.95, "Nectar Wholefood Price"),
            "STORE-TESCO-02": (5.80, 4.85, "Clubcard Healthy Snack Deal"),
            "STORE-LIDL-03": (4.49, 3.99, "Lidl Plus Alesto Offer"),
            "STORE-WAITROSE-04": (6.75, 5.95, "Waitrose Duchy Wholefoods"),
            "STORE-COSTCO-05": (4.50, 3.65, "Kirkland 1.13kg Bag Split"),
            "STORE-ONLINE-AMAZON": (3.95, 2.85, "Amazon Subscribe & Save -15%"),
            "STORE-ONLINE-GRAPETREE": (3.35, 2.39, "Grape Tree 1kg Bulk Value Winner"),
            "STORE-ONLINE-WHOLEFOODEARTH": (3.45, 2.45, "Whole Food Earth Sustainable 1kg Split"),
        },
    },
]

_AMBIENT_WHOLEFOOD_KEYWORDS = (
    "almond", "walnut", "cashew", "nut", "seed", "chia", "flax", "pumpkin",
    "sunflower", "oat", "porridge", "muesli", "granola", "lentil", "chickpea",
    "bean", "pulse", "quinoa", "rice", "grain", "pasta", "spaghetti", "penne",
    "noodle", "flour", "sugar", "honey", "syrup", "oil", "olive oil", "vinegar",
    "coffee", "espresso", "tea", "cocoa", "cacao", "chocolate", "spice", "herb",
    "cinnamon", "turmeric", "cumin", "paprika", "raisin", "sultana", "date",
    "apricot", "fig", "cranberr", "dried", "wholefood", "cereal", "biscuit",
    "cracker", "tin", "canned", "vitamin", "supplement", "protein powder",
)


def _classify_item_category(query: str) -> str:
  """Classifies whether a shopping item is AMBIENT_WHOLEFOOD (shippable by online wholefood/pantry retailers) or FRESH_CHILLED."""
  q = query.strip().lower()
  for entry in CANONICAL_CATALOG:
    for kw in entry["keywords"]:
      if kw in q or q in kw:
        return str(entry.get("item_category", "FRESH_CHILLED"))
  for kw in _AMBIENT_WHOLEFOOD_KEYWORDS:
    if kw in q:
      return "AMBIENT_WHOLEFOOD"
  return "FRESH_CHILLED"


def _normalize_quantity_multiplier(requested_qty: float, requested_unit: str) -> float:
  """Normalizes metric sub-units (e.g., 500g -> 0.5kg, 500ml -> 0.5L)."""
  u = requested_unit.strip().lower()
  if u in ("g", "gram", "grams") and requested_qty >= 100:
    return requested_qty / 1000.0
  if u in ("ml", "milliliter", "milliliters") and requested_qty >= 100:
    return requested_qty / 1000.0
  return requested_qty


def _match_item_to_sku(
    item: ShoppingItemInput, store_id: str
) -> tuple[str, str, float, float, str | None, bool, str] | None:
  """Matches a user shopping item to a store SKU, returning None if the online store cannot stock fresh/chilled items."""
  query = item.name.strip().lower()
  is_online_store = store_id.startswith("STORE-ONLINE-")

  for entry in CANONICAL_CATALOG:
    for kw in entry["keywords"]:
      if kw in query or query in kw:
        item_cat = str(entry.get("item_category", "FRESH_CHILLED"))
        if store_id not in entry["prices"]:
          # This store does not stock this item (e.g., online shop asked for fresh milk/chicken/eggs)
          return None
        reg_price, loy_price, badge = entry["prices"][store_id]
        return (
            entry["sku_id"],
            entry["product_name"],
            reg_price,
            loy_price,
            badge,
            False,
            item_cat,
        )

  item_cat = _classify_item_category(query)
  if is_online_store and item_cat == "FRESH_CHILLED":
    # Online wholefood/ambient retailers cannot fulfill custom fresh/chilled items
    return None

  digest = int(hashlib.sha256(query.encode("utf-8")).hexdigest()[:8], 16)
  base_price = round(1.45 + (digest % 420) / 100.0, 2)
  store_multipliers = {
      "STORE-SAINSBURYS-01": (1.03, 0.87, "Nectar Price Custom Deal"),
      "STORE-TESCO-02": (1.01, 0.85, "Clubcard Price Custom Deal"),
      "STORE-LIDL-03": (0.86, 0.77, "Lidl Plus App Offer"),
      "STORE-WAITROSE-04": (1.18, 1.06, "myWaitrose Selection"),
      "STORE-COSTCO-05": (0.88, 0.74, "Costco Wholesale Member Rate"),
      "STORE-ONLINE-AMAZON": (0.88, 0.72, "Amazon Subscribe & Save -15%"),
      "STORE-ONLINE-GRAPETREE": (0.78, 0.64, "Grape Tree Bulk Wholefood Deal"),
      "STORE-ONLINE-WHOLEFOODEARTH": (0.77, 0.63, "Whole Food Earth Eco Bulk Rate"),
  }
  reg_mult, loy_mult, badge = store_multipliers.get(
      store_id, (1.0, 0.88, None)
  )
  sku_slug = "".join(ch if ch.isalnum() else "-" for ch in query.upper())[:14]
  return (
      f"SKU-UK-{sku_slug}",
      f"{item.name.title()} (UK Pack)",
      round(base_price * reg_mult, 2),
      round(base_price * loy_mult, 2),
      badge,
      True,
      item_cat,
  )


def analyze_loyalty_advantage(
    store: GroceryStore,
    regular_subtotal: float,
    loyalty_subtotal: float,
    user_active_programs: list[str],
    trips_per_year: int = 52,
) -> LoyaltyAdvantageAnalysis:
  """Evaluates whether being a loyalty member at `store` is advantageous in GBP (£)."""
  lp = store.loyalty_program
  already_member = lp.program_id in user_active_programs

  effective_annual_fee = 0.0 if already_member else lp.annual_fee
  amortized_weekly_fee = round(effective_annual_fee / max(1, trips_per_year), 2)

  gross_weekly_discount = round(max(0.0, regular_subtotal - loyalty_subtotal), 2)
  points_cashback = round(loyalty_subtotal * lp.points_cashback_rate, 2)
  total_weekly_benefit = round(gross_weekly_discount + points_cashback, 2)
  net_weekly_advantage = round(total_weekly_benefit - amortized_weekly_fee, 2)
  projected_annual_net = round(
      total_weekly_benefit * trips_per_year - effective_annual_fee, 2
  )

  if lp.annual_fee <= 0.0:
    breakeven_weeks = 0.0
  elif total_weekly_benefit > 0:
    breakeven_weeks = round(lp.annual_fee / total_weekly_benefit, 1)
  else:
    breakeven_weeks = None

  is_advantageous = net_weekly_advantage > 0.0

  if already_member:
    tier = LoyaltyRecommendationTier.ALREADY_MEMBER_ACTIVE
    fee_note = (
        f"your existing £{lp.annual_fee:.2f}/yr membership is already active (£0.00 incremental fee)"
        if lp.annual_fee > 0
        else "you are an active member (£0.00 annual fee)"
    )
    rationale = (
        f"ACTIVE MEMBER ADVANTAGE: Because {fee_note}, using {lp.program_name} "
        f"saves £{gross_weekly_discount:.2f} immediately plus £{points_cashback:.2f} in rewards "
        f"(+£{total_weekly_benefit:.2f}/wk benefit, or +£{projected_annual_net:.2f}/yr)."
    )
  elif lp.annual_fee == 0.0 and total_weekly_benefit > 0:
    tier = LoyaltyRecommendationTier.HIGHLY_ADVANTAGEOUS_FREE
    rationale = (
        f"HIGHLY ADVANTAGEOUS (Free Enrolment): {lp.program_name} has a £0.00 annual fee "
        f"and saves you £{total_weekly_benefit:.2f}/wk on eligible items "
        f"(+£{projected_annual_net:.2f}/yr projected savings)."
    )
  elif is_advantageous and (breakeven_weeks is not None and breakeven_weeks <= 16.0):
    tier = LoyaltyRecommendationTier.HIGHLY_ADVANTAGEOUS_PAID
    rationale = (
        f"HIGHLY ADVANTAGEOUS (Paid Membership ROI): {lp.program_name} costs £{lp.annual_fee:.2f}/yr "
        f"(£{amortized_weekly_fee:.2f}/wk amortised), but yields £{total_weekly_benefit:.2f}/wk "
        f"in member discounts & rebates. Net advantage is +£{net_weekly_advantage:.2f}/wk "
        f"(+£{projected_annual_net:.2f}/yr), breaking even in {breakeven_weeks} weekly shops."
    )
  elif is_advantageous:
    tier = LoyaltyRecommendationTier.MARGINAL_PAYBACK
    rationale = (
        f"MODERATELY ADVANTAGEOUS: {lp.program_name} (£{lp.annual_fee:.2f}/yr) yields "
        f"+£{net_weekly_advantage:.2f}/wk net benefit after fee amortisation, "
        f"requiring {breakeven_weeks} weekly trips to break even."
    )
  else:
    tier = LoyaltyRecommendationTier.NOT_ADVANTAGEOUS
    rationale = (
        f"NOT ADVANTAGEOUS FOR THIS BASKET: {lp.program_name} costs £{lp.annual_fee:.2f}/yr "
        f"(£{amortized_weekly_fee:.2f}/wk), which exceeds this basket's weekly benefit "
        f"of £{total_weekly_benefit:.2f}."
    )

  return LoyaltyAdvantageAnalysis(
      store_id=store.store_id,
      store_name=store.name,
      program_name=lp.program_name,
      user_already_member=already_member,
      annual_membership_fee=lp.annual_fee,
      amortized_weekly_fee=amortized_weekly_fee,
      gross_weekly_loyalty_discount=gross_weekly_discount,
      points_cashback_value=points_cashback,
      total_weekly_member_benefit=total_weekly_benefit,
      net_weekly_advantage=net_weekly_advantage,
      projected_annual_net_savings=projected_annual_net,
      breakeven_weeks=breakeven_weeks,
      is_advantageous=is_advantageous,
      recommendation_tier=tier,
      rationale=rationale,
  )


def fetch_store_catalog_quote(
    store: GroceryStore,
    items: list[ShoppingItemInput],
    user_active_programs: list[str],
    fuel_cost_per_km: float = 0.18,
    historical_price_lookup: dict[str, float] | None = None,
) -> StoreBasketQuote:
  """Computes a GBP (£) basket quote and validates whether an online store can fulfill the entire list."""
  historical_price_lookup = historical_price_lookup or {}
  matched_items: list[MatchedLineItem] = []
  missing_items: list[str] = []
  regular_subtotal = 0.0
  loyalty_subtotal = 0.0

  for item in items:
    matched = _match_item_to_sku(item, store.store_id)
    if matched is None:
      missing_items.append(
          f"{item.name} ({item.quantity:g} {item.unit}) — Fresh/Chilled item not stocked online by {store.chain}"
      )
      continue

    sku_id, prod_name, reg_unit, loy_unit, badge, is_sub, item_cat = matched
    eff_qty = _normalize_quantity_multiplier(item.quantity, item.unit)
    reg_line = round(reg_unit * eff_qty, 2)
    loy_line = round(loy_unit * eff_qty, 2)
    savings_line = round(reg_line - loy_line, 2)

    hist_avg = historical_price_lookup.get(sku_id)
    pct_diff = None
    if hist_avg and hist_avg > 0:
      pct_diff = round(((loy_unit - hist_avg) / hist_avg) * 100.0, 1)

    matched_items.append(
        MatchedLineItem(
            requested_item=item.name,
            matched_sku_id=sku_id,
            matched_product_name=prod_name,
            quantity=item.quantity,
            unit=item.unit,
            regular_unit_price=reg_unit,
            loyalty_unit_price=loy_unit,
            regular_line_total=reg_line,
            loyalty_line_total=loy_line,
            loyalty_savings=savings_line,
            is_substituted=is_sub,
            promo_badge=badge,
            historical_avg_price=hist_avg,
            price_vs_history_pct=pct_diff,
            item_category=item_cat,
        )
    )
    regular_subtotal = round(regular_subtotal + reg_line, 2)
    loyalty_subtotal = round(loyalty_subtotal + loy_line, 2)

  loyalty_analysis = analyze_loyalty_advantage(
      store=store,
      regular_subtotal=regular_subtotal,
      loyalty_subtotal=loyalty_subtotal,
      user_active_programs=user_active_programs,
  )

  if store.store_type == "ONLINE_UK":
    if not matched_items:
      roundtrip_fuel = 0.0
      reg_delivery = 0.0
    elif (
        loyalty_subtotal >= store.free_delivery_threshold
        or store.loyalty_program.program_id == "LP-AMAZON-PRIME"
    ):
      roundtrip_fuel = 0.0
      reg_delivery = (
          0.0
          if regular_subtotal >= store.free_delivery_threshold
          else store.standard_delivery_fee
      )
    else:
      roundtrip_fuel = store.standard_delivery_fee
      reg_delivery = store.standard_delivery_fee
  else:
    roundtrip_fuel = round(store.distance_km * 2.0 * fuel_cost_per_km, 2)
    reg_delivery = roundtrip_fuel

  effective_loyalty_basket_cost = round(
      loyalty_subtotal
      + loyalty_analysis.amortized_weekly_fee
      - loyalty_analysis.points_cashback_value
      + roundtrip_fuel,
      2,
  )
  total_regular_with_travel = round(regular_subtotal + reg_delivery, 2)
  total_loyalty_with_travel = round(
      loyalty_subtotal + loyalty_analysis.amortized_weekly_fee + roundtrip_fuel,
      2,
  )

  if loyalty_analysis.is_advantageous:
    effective_best_total = effective_loyalty_basket_cost
    effective_uses_loyalty = True
  else:
    effective_best_total = total_regular_with_travel
    effective_uses_loyalty = False

  total_req = len(items)
  fulfilled_cnt = len(matched_items)
  can_fulfill_all = (len(missing_items) == 0 and fulfilled_cnt == total_req)
  coverage_pct = round((fulfilled_cnt / max(1, total_req)) * 100.0, 1)

  if can_fulfill_all:
    validity_note = (
        f"VALID FULL-LIST RETAILER ({fulfilled_cnt}/{total_req} items, 100%): "
        f"{store.name} stocks all fresh, chilled, bakery & pantry items on your list."
    )
  else:
    supported_names = ", ".join(m.requested_item for m in matched_items) or "None"
    missing_short = ", ".join(
        m.split(" (")[0] for m in missing_items[:5]
    ) + ("..." if len(missing_items) > 5 else "")
    validity_note = (
        f"PARTIAL ONLINE FULFILMENT ONLY ({fulfilled_cnt}/{total_req} items, {coverage_pct}%): "
        f"{store.name} CANNOT fulfill your whole list standalone. It stocks ambient wholefoods/pantry "
        f"({supported_names}), but DOES NOT stock fresh/chilled perishables ({missing_short}). "
        f"Purchase eligible dry items online and the rest at a regular 20km supermarket."
    )

  return StoreBasketQuote(
      store=store,
      line_items=matched_items,
      missing_items=missing_items,
      regular_subtotal=regular_subtotal,
      loyalty_subtotal=loyalty_subtotal,
      estimated_roundtrip_fuel_cost=roundtrip_fuel,
      total_regular_with_travel=total_regular_with_travel,
      total_loyalty_with_travel=total_loyalty_with_travel,
      effective_best_total=effective_best_total,
      effective_uses_loyalty=effective_uses_loyalty,
      loyalty_analysis=loyalty_analysis,
      can_fulfill_entire_list=can_fulfill_all,
      fulfilled_item_count=fulfilled_cnt,
      total_requested_item_count=total_req,
      fulfillment_coverage_pct=coverage_pct,
      online_validity_note=validity_note,
  )


def build_online_plus_regular_shop_plan(
    store_quotes: list[StoreBasketQuote],
    fuel_cost_per_km: float = 0.18,
) -> SplitBasketOption | None:
  """Creates an explicit 'Purchase Certain Items Online + Rest from a Regular 20km Shop' plan.

  When online retailers (Grape Tree, Whole Food Earth, Amazon UK) only support ambient/wholefood
  items and cannot fulfill fresh/chilled perishables, this planner allocates the cheaper ambient
  wholefoods to the best Online Retailer and allocates all remaining fresh/chilled/perishable
  items to the best 20km Regular Supermarket.
  """
  physical_quotes = [
      q
      for q in store_quotes
      if q.store.store_type == "PHYSICAL_20KM" and q.can_fulfill_entire_list
  ]
  online_quotes = [
      q
      for q in store_quotes
      if q.store.store_type == "ONLINE_UK" and len(q.line_items) > 0
  ]
  if not physical_quotes or not online_quotes:
    return None

  best_single_physical = min(physical_quotes, key=lambda q: q.effective_best_total)
  best_hybrid: SplitBasketOption | None = None
  best_item_savings = -9999.0

  for onl_q in online_quotes:
    online_by_req = {li.requested_item: li for li in onl_q.line_items}
    for phys_q in physical_quotes:
      alloc_online: list[MatchedLineItem] = []
      alloc_phys: list[MatchedLineItem] = []
      sub_online = 0.0
      sub_phys = 0.0
      gross_item_savings_vs_phys = 0.0

      for phys_item in phys_q.line_items:
        p_phys = (
            phys_item.loyalty_line_total
            if phys_q.effective_uses_loyalty
            else phys_item.regular_line_total
        )
        onl_item = online_by_req.get(phys_item.requested_item)
        if onl_item is not None:
          p_onl = (
              onl_item.loyalty_line_total
              if onl_q.effective_uses_loyalty
              else onl_item.regular_line_total
          )
          if p_onl < p_phys:
            alloc_online.append(onl_item)
            sub_online = round(sub_online + p_onl, 2)
            gross_item_savings_vs_phys = round(
                gross_item_savings_vs_phys + (p_phys - p_onl), 2
            )
            continue

        alloc_phys.append(phys_item)
        sub_phys = round(sub_phys + p_phys, 2)

      if not alloc_online or not alloc_phys:
        continue

      # Physical 20km return trip fuel
      route_km = round(phys_q.store.distance_km * 2.0, 2)
      phys_fuel = round(route_km * fuel_cost_per_km, 2)

      # Online delivery fee check: waived if above free_delivery_threshold or if Amazon Prime
      # Note: Because ambient wholefoods (nuts, seeds, olive oil, coffee, pasta) have a 6-12 month
      # shelf life, shoppers typically bundle 3-4 weeks of wholefoods (or use Prime) for £0 delivery.
      if (
          sub_online >= onl_q.store.free_delivery_threshold
          or onl_q.store.loyalty_program.program_id == "LP-AMAZON-PRIME"
          or onl_q.loyalty_analysis.user_already_member
      ):
        online_deliv_fee = 0.0
      else:
        # Amortize monthly wholefood bulk order delivery across 4 weekly shops
        online_deliv_fee = round(onl_q.store.standard_delivery_fee / 4.0, 2)

      total_travel_and_deliv = round(phys_fuel + online_deliv_fee, 2)

      fees = 0.0
      cashback = 0.0
      if onl_q.effective_uses_loyalty:
        fees += onl_q.loyalty_analysis.amortized_weekly_fee
        cashback += round(
            sub_online * onl_q.store.loyalty_program.points_cashback_rate, 2
        )
      if phys_q.effective_uses_loyalty:
        fees += phys_q.loyalty_analysis.amortized_weekly_fee
        cashback += round(
            sub_phys * phys_q.store.loyalty_program.points_cashback_rate, 2
        )

      combined_sub = round(sub_online + sub_phys, 2)
      total_with_travel = round(
          combined_sub + fees - cashback + total_travel_and_deliv, 2
      )
      net_savings_vs_single = round(
          best_single_physical.effective_best_total - total_with_travel, 2
      )

      online_names_str = ", ".join(i.requested_item for i in alloc_online)
      phys_names_str = ", ".join(i.requested_item for i in alloc_phys[:5]) + (
          f" (+{len(alloc_phys) - 5} more)" if len(alloc_phys) > 5 else ""
      )

      validity_summary = (
          f"VALIDITY CHECK: {onl_q.store.name} CANNOT fulfill your entire {len(phys_q.line_items)}-item list standalone "
          f"(it only stocks {len(onl_q.line_items)} ambient/wholefood items and cannot supply {len(onl_q.missing_items)} "
          f"fresh/chilled items such as {', '.join(m.split(' (')[0] for m in onl_q.missing_items[:4])})."
      )
      free_deliv_tip = (
          f"Online Delivery Tip: {onl_q.store.name} offers FREE UK delivery on orders over "
          f"£{onl_q.store.free_delivery_threshold:.2f} (standard fee £{onl_q.store.standard_delivery_fee:.2f}). "
          f"Stocking up on non-perishable wholefoods ({online_names_str}) once a month waives the delivery fee completely."
      )
      rationale = (
          f"PURCHASE ONLINE + REGULAR SHOP PLAN: Buy {len(alloc_online)} ambient/wholefood items ONLINE from "
          f"{onl_q.store.name} ({online_names_str} — £{sub_online:.2f}, saving £{gross_item_savings_vs_phys:.2f} on those items vs supermarket prices) "
          f"AND purchase the remaining {len(alloc_phys)} fresh/chilled items in-store at {phys_q.store.name} "
          f"({phys_names_str} — £{sub_phys:.2f} + £{phys_fuel:.2f} return fuel for {route_km}km). "
          f"Combined 100%-complete basket total is £{total_with_travel:.2f} "
          f"({'saving £' + f'{net_savings_vs_single:.2f}/wk' if net_savings_vs_single > 0 else 'within £' + f'{abs(net_savings_vs_single):.2f}/wk'} "
          f"vs buying 100% in-store at {best_single_physical.store.name} for £{best_single_physical.effective_best_total:.2f})."
      )

      candidate = SplitBasketOption(
          stores=[
              SplitStoreAllocation(
                  store_id=onl_q.store.store_id,
                  store_name=f"[ONLINE ORDER] {onl_q.store.name}",
                  distance_km=0.0,
                  use_loyalty=onl_q.effective_uses_loyalty,
                  assigned_items=alloc_online,
                  subtotal=sub_online,
                  store_type="ONLINE_UK",
                  delivery_or_fuel_fee=online_deliv_fee,
              ),
              SplitStoreAllocation(
                  store_id=phys_q.store.store_id,
                  store_name=f"[REGULAR 20KM SHOP] {phys_q.store.name}",
                  distance_km=phys_q.store.distance_km,
                  use_loyalty=phys_q.effective_uses_loyalty,
                  assigned_items=alloc_phys,
                  subtotal=sub_phys,
                  store_type="PHYSICAL_20KM",
                  delivery_or_fuel_fee=phys_fuel,
              ),
          ],
          combined_item_subtotal=combined_sub,
          multi_stop_route_km=route_km,
          multi_stop_fuel_cost=total_travel_and_deliv,
          total_cost_with_travel=total_with_travel,
          savings_vs_best_single_store=net_savings_vs_single,
          is_recommended_over_single=net_savings_vs_single >= 0.25,
          rationale=rationale,
          plan_type="ONLINE_PLUS_REGULAR_SHOP",
          online_validity_summary=validity_summary,
          free_delivery_tip=free_deliv_tip,
      )

      if (
          best_hybrid is None
          or candidate.total_cost_with_travel < best_hybrid.total_cost_with_travel
          or (
              candidate.total_cost_with_travel == best_hybrid.total_cost_with_travel
              and gross_item_savings_vs_phys > best_item_savings
          )
      ):
        best_hybrid = candidate
        best_item_savings = gross_item_savings_vs_phys

  return best_hybrid


def optimize_split_basket_strategy(
    store_quotes: list[StoreBasketQuote],
    user_location: GeoCoordinate,
    fuel_cost_per_km: float = 0.18,
    min_net_savings_threshold: float = 0.50,
) -> SplitBasketOption | None:
  """Finds the best 2-store split-basket strategy (prioritizing Online + Regular 20km Shop when beneficial)."""
  if len(store_quotes) < 2:
    return None

  # 1. Evaluate Online + Regular 20km Shop hybrid plan first
  hybrid_plan = build_online_plus_regular_shop_plan(
      store_quotes=store_quotes, fuel_cost_per_km=fuel_cost_per_km
  )

  # 2. Also evaluate 2 physical 20km stores that can fulfill the full list
  full_quotes = [q for q in store_quotes if q.can_fulfill_entire_list]
  if not full_quotes:
    return hybrid_plan

  best_single = min(full_quotes, key=lambda q: q.effective_best_total)
  best_option: SplitBasketOption | None = hybrid_plan

  for i in range(len(full_quotes)):
    for j in range(i + 1, len(full_quotes)):
      qa = full_quotes[i]
      qb = full_quotes[j]

      alloc_a: list[MatchedLineItem] = []
      alloc_b: list[MatchedLineItem] = []
      sub_a = 0.0
      sub_b = 0.0

      qb_map = {li.requested_item: li for li in qb.line_items}
      for item_a in qa.line_items:
        item_b = qb_map.get(item_a.requested_item)
        if item_b is None:
          alloc_a.append(item_a)
          price_a = (
              item_a.loyalty_line_total
              if qa.effective_uses_loyalty
              else item_a.regular_line_total
          )
          sub_a = round(sub_a + price_a, 2)
          continue

        price_a = (
            item_a.loyalty_line_total
            if qa.effective_uses_loyalty
            else item_a.regular_line_total
        )
        price_b = (
            item_b.loyalty_line_total
            if qb.effective_uses_loyalty
            else item_b.regular_line_total
        )
        if price_a <= price_b:
          alloc_a.append(item_a)
          sub_a = round(sub_a + price_a, 2)
        else:
          alloc_b.append(item_b)
          sub_b = round(sub_b + price_b, 2)

      if not alloc_a or not alloc_b:
        continue

      leg_ab = haversine_distance_km(qa.store.coordinate, qb.store.coordinate)
      route_km = round(qa.store.distance_km + leg_ab + qb.store.distance_km, 2)
      route_fuel = round(route_km * fuel_cost_per_km, 2)

      fees = 0.0
      cashback = 0.0
      if qa.effective_uses_loyalty:
        fees += qa.loyalty_analysis.amortized_weekly_fee
        cashback += round(sub_a * qa.store.loyalty_program.points_cashback_rate, 2)
      if qb.effective_uses_loyalty:
        fees += qb.loyalty_analysis.amortized_weekly_fee
        cashback += round(sub_b * qb.store.loyalty_program.points_cashback_rate, 2)

      combined_subtotal = round(sub_a + sub_b, 2)
      total_with_travel = round(combined_subtotal + fees - cashback + route_fuel, 2)
      net_savings = round(best_single.effective_best_total - total_with_travel, 2)

      candidate = SplitBasketOption(
          stores=[
              SplitStoreAllocation(
                  store_id=qa.store.store_id,
                  store_name=qa.store.name,
                  distance_km=qa.store.distance_km,
                  use_loyalty=qa.effective_uses_loyalty,
                  assigned_items=alloc_a,
                  subtotal=sub_a,
                  store_type=qa.store.store_type,
              ),
              SplitStoreAllocation(
                  store_id=qb.store.store_id,
                  store_name=qb.store.name,
                  distance_km=qb.store.distance_km,
                  use_loyalty=qb.effective_uses_loyalty,
                  assigned_items=alloc_b,
                  subtotal=sub_b,
                  store_type=qb.store.store_type,
              ),
          ],
          combined_item_subtotal=combined_subtotal,
          multi_stop_route_km=route_km,
          multi_stop_fuel_cost=route_fuel,
          total_cost_with_travel=total_with_travel,
          savings_vs_best_single_store=net_savings,
          is_recommended_over_single=net_savings >= min_net_savings_threshold,
          rationale=(
              f"{route_km}km 2-store loop: Buying {len(alloc_a)} items at {qa.store.name} (£{sub_a:.2f}) and "
              f"{len(alloc_b)} items at {qb.store.name} (£{sub_b:.2f}) "
              f"{'saves an extra £' + f'{net_savings:.2f}' if net_savings > 0 else 'costs £' + f'{abs(net_savings):.2f} more'} "
              f"compared to buying everything at {best_single.store.name} (£{best_single.effective_best_total:.2f})."
          ),
          plan_type="TWO_STORE_SPLIT",
      )

      if (
          best_option is None
          or candidate.total_cost_with_travel < best_option.total_cost_with_travel
      ):
        best_option = candidate

  return best_option
