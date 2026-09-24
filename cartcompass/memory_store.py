"""Persistent Context & Memory Store (SQLite-backed) for Multi-Run Weekly Shopping Lists."""

from __future__ import annotations

import contextlib
from dataclasses import asdict
import datetime
import json
import os
import sqlite3
from typing import Any, Iterator
import uuid

from cartcompass.models import GeoCoordinate, ShoppingItemInput


DEFAULT_UK_LOYALTY_PROGRAMS: list[str] = [
    "LP-TESCO-CLUBCARD",
    "LP-SAINSBURYS-NECTAR",
    "LP-LIDL-PLUS",
    "LP-COSTCO-GOLDSTAR",
]


class PersistentMemoryStore:
  """Manages Short-Term Session Context and Long-Term Episodic/Semantic Memory.

  Supports adding a new weekly shopping list on every run while preserving:
  1. Episodic Memory: Past weekly shopping lists, winning recommendations, and
     cumulative loyalty & basket savings over time (in GBP £).
  2. Semantic User Profile Memory: Home coordinates in Eastergate, West Sussex, UK
     (50.845561, -0.643677), default 20km radius, active loyalty memberships
     (Tesco, Sainsbury's, Lidl, Costco), and recurring staple frequency.
  3. Price Memory: Rolling historical SKU prices per store in GBP (£).
  """

  def __init__(self, db_path: str | None = None) -> None:
    if db_path is None:
      base_dir = os.environ.get(
          "GROCERY_APP_STATE_DIR",
          "/tmp/grocery_price_optimizer_state",
      )
      os.makedirs(base_dir, exist_ok=True)
      db_path = os.path.join(base_dir, "grocery_memory_gbp_v2.sqlite3")
    self.db_path = db_path
    self._init_db()

  @contextlib.contextmanager
  def _connect(self) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    try:
      with conn:
        yield conn
    finally:
      conn.close()

  def _init_db(self) -> None:
    with self._connect() as conn:
      conn.executescript(
          """
          CREATE TABLE IF NOT EXISTS user_profiles (
              user_id TEXT PRIMARY KEY,
              home_latitude REAL NOT NULL,
              home_longitude REAL NOT NULL,
              home_label TEXT NOT NULL,
              default_radius_km REAL NOT NULL DEFAULT 20.0,
              fuel_cost_per_km REAL NOT NULL DEFAULT 0.18,
              active_loyalty_programs_json TEXT NOT NULL,
              updated_at_iso TEXT NOT NULL
          );

          CREATE TABLE IF NOT EXISTS shopping_lists (
              list_id TEXT PRIMARY KEY,
              user_id TEXT NOT NULL,
              title TEXT NOT NULL,
              created_at_iso TEXT NOT NULL,
              items_json TEXT NOT NULL,
              winning_strategy_type TEXT,
              winning_store_summary TEXT,
              winning_total_cost REAL,
              loyalty_savings_usd REAL,
              recommendation_json TEXT
          );

          CREATE TABLE IF NOT EXISTS item_frequency_memory (
              user_id TEXT NOT NULL,
              normalized_name TEXT NOT NULL,
              display_name TEXT NOT NULL,
              default_unit TEXT NOT NULL,
              last_quantity REAL NOT NULL,
              times_ordered INTEGER NOT NULL DEFAULT 1,
              last_ordered_iso TEXT NOT NULL,
              PRIMARY KEY (user_id, normalized_name)
          );

          CREATE TABLE IF NOT EXISTS sku_price_history (
              sku_id TEXT PRIMARY KEY,
              product_name TEXT NOT NULL,
              rolling_avg_price REAL NOT NULL,
              samples_count INTEGER NOT NULL DEFAULT 1,
              updated_at_iso TEXT NOT NULL
          );
          """
      )
      self._seed_default_profile_if_empty(conn)

  def _seed_default_profile_if_empty(self, conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT user_id FROM user_profiles WHERE user_id = ?", ("mrmitchell",)
    ).fetchone()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    default_label = "Home (Eastergate, West Sussex, UK)"
    if not row:
      conn.execute(
          """
          INSERT INTO user_profiles (
              user_id, home_latitude, home_longitude, home_label,
              default_radius_km, fuel_cost_per_km,
              active_loyalty_programs_json, updated_at_iso
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
          """,
          (
              "mrmitchell",
              50.845561,
              -0.643677,
              default_label,
              20.0,
              0.18,
              json.dumps(DEFAULT_UK_LOYALTY_PROGRAMS),
              now_iso,
          ),
      )
    else:
      conn.execute(
          """
          UPDATE user_profiles
          SET home_latitude = ?,
              home_longitude = ?,
              home_label = ?,
              default_radius_km = 20.0,
              fuel_cost_per_km = 0.18,
              active_loyalty_programs_json = ?,
              updated_at_iso = ?
          WHERE user_id = ?
          """,
          (
              50.845561,
              -0.643677,
              default_label,
              json.dumps(DEFAULT_UK_LOYALTY_PROGRAMS),
              now_iso,
              "mrmitchell",
          ),
      )

    # Seed UK GBP (£) baseline historical prices for realistic deal detection
    baseline_skus = [
        ("SKU-MILK-2L", "British Semi-Skimmed Milk (2.27L / 4 Pints)", 1.65),
        ("SKU-EGGS-12", "British Free-Range Large Eggs (12 Pack)", 3.15),
        ("SKU-BREAD-LOAF", "Artisan White Sourdough Bloomer (800g)", 2.25),
        ("SKU-CHICKEN-KG", "British Chicken Breast Fillets (1kg)", 6.90),
        ("SKU-APPLES-KG", "Sussex Braeburn & Gala Apples (1kg)", 2.40),
        ("SKU-PASTA-PACK", "Italian Durum Wheat Penne Pasta (500g)", 1.25),
        ("SKU-COFFEE-PACK", "Rich Roast Arabica Ground Coffee (400g)", 4.85),
        ("SKU-OLIVEOIL-L", "Extra Virgin Cold-Pressed Olive Oil (1L)", 7.50),
        ("SKU-YOGURT-PACK", "Authentic Greek Style Natural Yogurt (500g)", 1.85),
        ("SKU-SALMON-KG", "Scottish Atlantic Salmon Fillets (1kg)", 16.50),
        ("SKU-SPINACH-PACK", "Triple-Washed Baby Spinach (250g)", 1.60),
        ("SKU-CHEDDAR-PACK", "Cathedral Vintage Mature Cheddar (400g)", 3.75),
    ]
    for sku_id, name, avg_price in baseline_skus:
      conn.execute(
          """
          INSERT OR REPLACE INTO sku_price_history
          (sku_id, product_name, rolling_avg_price, samples_count, updated_at_iso)
          VALUES (?, ?, ?, ?, ?)
          """,
          (sku_id, name, avg_price, 8, now_iso),
      )

  def get_user_profile(self, user_id: str = "mrmitchell") -> dict[str, Any]:
    with self._connect() as conn:
      row = conn.execute(
          "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
      ).fetchone()
      if not row:
        self._seed_default_profile_if_empty(conn)
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
      home_label_str = str(row["home_label"] or "")
      extracted_postcode = "PO20 3SJ"
      if "(Postcode " in home_label_str:
        extracted_postcode = (
            home_label_str.split("(Postcode ", 1)[1].split(")", 1)[0].strip()
        )
      else:
        import re as _re

        m = _re.search(
            r"\(([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}|[A-Z]{1,2}\d[A-Z\d]?)\)",
            home_label_str,
        )
        if m:
          extracted_postcode = m.group(1).strip()
      return {
          "user_id": row["user_id"],
          "home_coordinate": GeoCoordinate(
              latitude=row["home_latitude"],
              longitude=row["home_longitude"],
              label=home_label_str,
              postcode=extracted_postcode,
          ),
          "default_radius_km": float(row["default_radius_km"]),
          "fuel_cost_per_km": float(row["fuel_cost_per_km"]),
          "active_loyalty_programs": json.loads(
              row["active_loyalty_programs_json"]
          ),
          "updated_at_iso": row["updated_at_iso"],
      }

  def update_user_profile(
      self,
      user_id: str = "mrmitchell",
      latitude: float | None = None,
      longitude: float | None = None,
      home_label: str | None = None,
      active_loyalty_programs: list[str] | None = None,
      default_radius_km: float | None = None,
  ) -> dict[str, Any]:
    profile = self.get_user_profile(user_id)
    new_lat = (
        latitude if latitude is not None else profile["home_coordinate"].latitude
    )
    new_lon = (
        longitude
        if longitude is not None
        else profile["home_coordinate"].longitude
    )
    new_label = (
        home_label if home_label is not None else profile["home_coordinate"].label
    )
    new_programs = (
        active_loyalty_programs
        if active_loyalty_programs is not None
        else profile["active_loyalty_programs"]
    )
    new_radius = (
        default_radius_km
        if default_radius_km is not None
        else profile["default_radius_km"]
    )
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with self._connect() as conn:
      conn.execute(
          """
          UPDATE user_profiles
          SET home_latitude = ?,
              home_longitude = ?,
              home_label = ?,
              default_radius_km = ?,
              active_loyalty_programs_json = ?,
              updated_at_iso = ?
          WHERE user_id = ?
          """,
          (
              new_lat,
              new_lon,
              new_label,
              new_radius,
              json.dumps(new_programs),
              now_iso,
              user_id,
          ),
      )
    return self.get_user_profile(user_id)

  def record_new_shopping_list_run(
      self,
      user_id: str,
      title: str,
      items: list[ShoppingItemInput],
      winning_strategy_type: str,
      winning_store_summary: str,
      winning_total_cost: float,
      loyalty_savings_usd: float,
      recommendation_dict: dict[str, Any],
      list_id: str | None = None,
  ) -> str:
    """Appends a new weekly shopping list and updates recurring staple memory."""
    list_id = list_id or f"LIST-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    serialized_items = [asdict(item) for item in items]

    with self._connect() as conn:
      conn.execute(
          """
          INSERT INTO shopping_lists (
              list_id, user_id, title, created_at_iso, items_json,
              winning_strategy_type, winning_store_summary,
              winning_total_cost, loyalty_savings_usd, recommendation_json
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          """,
          (
              list_id,
              user_id,
              title,
              now_iso,
              json.dumps(serialized_items),
              winning_strategy_type,
              winning_store_summary,
              round(winning_total_cost, 2),
              round(loyalty_savings_usd, 2),
              json.dumps(recommendation_dict),
          ),
      )
      for item in items:
        norm_name = item.name.strip().lower()
        existing = conn.execute(
            """
            SELECT times_ordered FROM item_frequency_memory
            WHERE user_id = ? AND normalized_name = ?
            """,
            (user_id, norm_name),
        ).fetchone()
        if existing:
          conn.execute(
              """
              UPDATE item_frequency_memory
              SET times_ordered = times_ordered + 1,
                  last_quantity = ?,
                  default_unit = ?,
                  last_ordered_iso = ?
              WHERE user_id = ? AND normalized_name = ?
              """,
              (item.quantity, item.unit, now_iso, user_id, norm_name),
          )
        else:
          conn.execute(
              """
              INSERT INTO item_frequency_memory (
                  user_id, normalized_name, display_name,
                  default_unit, last_quantity, times_ordered, last_ordered_iso
              ) VALUES (?, ?, ?, ?, ?, 1, ?)
              """,
              (
                  user_id,
                  norm_name,
                  item.name.strip(),
                  item.unit,
                  item.quantity,
                  now_iso,
              ),
          )
    return list_id

  def list_shopping_history(
      self, user_id: str = "mrmitchell", limit: int = 20
  ) -> list[dict[str, Any]]:
    with self._connect() as conn:
      rows = conn.execute(
          """
          SELECT list_id, user_id, title, created_at_iso, items_json,
                 winning_strategy_type, winning_store_summary,
                 winning_total_cost, loyalty_savings_usd
          FROM shopping_lists
          WHERE user_id = ?
          ORDER BY created_at_iso DESC
          LIMIT ?
          """,
          (user_id, limit),
      ).fetchall()
      result = []
      for r in rows:
        items = json.loads(r["items_json"])
        result.append({
            "list_id": r["list_id"],
            "user_id": r["user_id"],
            "title": r["title"],
            "created_at_iso": r["created_at_iso"],
            "item_count": len(items),
            "items": items,
            "winning_strategy_type": r["winning_strategy_type"],
            "winning_store_summary": r["winning_store_summary"],
            "winning_total_cost": r["winning_total_cost"],
            "loyalty_savings_usd": r["loyalty_savings_usd"],
        })
      return result

  def get_shopping_list_detail(self, list_id: str) -> dict[str, Any] | None:
    with self._connect() as conn:
      row = conn.execute(
          "SELECT * FROM shopping_lists WHERE list_id = ?", (list_id,)
      ).fetchone()
      if not row:
        return None
      return {
          "list_id": row["list_id"],
          "user_id": row["user_id"],
          "title": row["title"],
          "created_at_iso": row["created_at_iso"],
          "items": json.loads(row["items_json"]),
          "winning_strategy_type": row["winning_strategy_type"],
          "winning_store_summary": row["winning_store_summary"],
          "winning_total_cost": row["winning_total_cost"],
          "loyalty_savings_usd": row["loyalty_savings_usd"],
          "recommendation": (
              json.loads(row["recommendation_json"])
              if row["recommendation_json"]
              else None
          ),
      }

  def get_frequent_staples(
      self, user_id: str = "mrmitchell", limit: int = 10
  ) -> list[dict[str, Any]]:
    with self._connect() as conn:
      rows = conn.execute(
          """
          SELECT display_name, default_unit, last_quantity, times_ordered
          FROM item_frequency_memory
          WHERE user_id = ?
          ORDER BY times_ordered DESC, display_name ASC
          LIMIT ?
          """,
          (user_id, limit),
      ).fetchall()
      return [dict(r) for r in rows]

  def get_historical_sku_price(self, sku_id: str) -> float | None:
    with self._connect() as conn:
      row = conn.execute(
          "SELECT rolling_avg_price FROM sku_price_history WHERE sku_id = ?",
          (sku_id,),
      ).fetchone()
      return float(row["rolling_avg_price"]) if row else None
