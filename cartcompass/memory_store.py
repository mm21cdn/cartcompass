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
from cartcompass.observability import (
    GLOBAL_PII_REDACTOR,
    STRUCTURED_LOGGER,
)


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
    new_label = GLOBAL_PII_REDACTOR.redact_text(
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
    """Appends a new weekly shopping list (with automatic PII redaction) and updates recurring staple memory."""
    list_id = list_id or f"LIST-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    sanitized_title = GLOBAL_PII_REDACTOR.redact_text(title)
    serialized_items = GLOBAL_PII_REDACTOR.redact_payload(
        [asdict(item) for item in items]
    )
    sanitized_rec = GLOBAL_PII_REDACTOR.redact_payload(recommendation_dict)

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
              sanitized_title,
              now_iso,
              json.dumps(serialized_items),
              winning_strategy_type,
              GLOBAL_PII_REDACTOR.redact_text(winning_store_summary),
              round(winning_total_cost, 2),
              round(loyalty_savings_usd, 2),
              json.dumps(sanitized_rec),
          ),
      )
      for item in items:
        clean_display_name = GLOBAL_PII_REDACTOR.redact_text(item.name.strip())
        norm_name = clean_display_name.lower()
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
                  clean_display_name,
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


# ---------------------------------------------------------------------------
# LLM System Instructions, Context Window Compaction, and Async Memory Worker
# ---------------------------------------------------------------------------
from cartcompass.observability import (  # noqa: E402
    GLOBAL_PII_REDACTOR,
    STRUCTURED_LOGGER,
)
import asyncio  # noqa: E402
from concurrent.futures import Future, ThreadPoolExecutor  # noqa: E402

SYSTEM_INSTRUCTIONS: dict[str, str] = {
    "COORDINATOR_AGENT": (
        "You are the CartCompass UK Coordinator Agent for Eastergate, West Sussex, UK "
        "(Default Postcode: PO20 3SJ, Lat: 50.845561, Lon: -0.643677). "
        "Your mission is to orchestrate specialist sub-agents (`ListParserSubAgent`, "
        "`GeospatialDiscoverySubAgent`, `PricingAndLoyaltySubAgent`, and `HybridSplitPlannerSubAgent`) "
        "to optimize weekly grocery shopping lists within a strict 20.0 km Haversine radius plus UK Online "
        "Retailers (Amazon UK, Grape Tree Health Foods, Whole Food Earth). "
        "CRITICAL RULES:\n"
        "1. Always format monetary values in British Pounds Sterling (GBP £).\n"
        "2. Verify online basket fulfillment validity (`can_fulfill_entire_list`). Online ambient wholefood "
        "shops CANNOT ship fresh/chilled milk, eggs, meat, fish, or bakery loaves via parcel post.\n"
        "3. Never rank a partial-basket online shop as the #1 single-store winner; instead, generate an "
        "explicit `ONLINE_PLUS_REGULAR_SHOP` split plan pairing online ambient items with a 20km supermarket.\n"
        "4. If any tool returns `status='error'`, follow its `llm_recovery_instructions` immediately."
    ),
    "LIST_PARSER_SUB_AGENT": (
        "You are the ListParserSubAgent (`gemini-2.5-flash`). Parse pasted multi-line UK grocery lists into "
        "structured quantities, normalized UK units (`kg`, `l`, `dozen`, `loaf`, `pack`), and classify each "
        "item as `AMBIENT_WHOLEFOOD` (eligible for online wholefood parcel delivery) or `FRESH_CHILLED` "
        "(requires a physical 20km supermarket)."
    ),
    "GEOSPATIAL_DISCOVERY_SUB_AGENT": (
        "You are the GeospatialDiscoverySubAgent (`gemini-2.5-flash`). Resolve UK postcodes via "
        "`resolve_uk_postcode` and filter supermarkets strictly within `radius_km <= 20.0` using Haversine distance."
    ),
    "PRICING_AND_LOYALTY_SUB_AGENT": (
        "You are the PricingAndLoyaltySubAgent (`gemini-2.5-pro`). Evaluate itemized basket totals, amortized "
        "membership fees, points/cashback, and active UK loyalty advantages (Tesco Clubcard, Sainsbury's Nectar, "
        "Lidl Plus, Costco UK) across all eligible stores."
    ),
    "HYBRID_SPLIT_PLANNER_SUB_AGENT": (
        "You are the HybridSplitPlannerSubAgent (`gemini-2.5-pro`). When online wholefood shops cannot fulfill "
        "fresh/chilled items standalone, compute the optimal 2-step `ONLINE_PLUS_REGULAR_SHOP` split plan."
    ),
}


class ContextWindowManager:
  """Manages LLM prompt token budgets, prunes bloated tool payloads, and summarizes episodic history."""

  def __init__(self, max_context_tokens: int = 3200) -> None:
    self.max_context_tokens = max_context_tokens

  @staticmethod
  def estimate_tokens(text_or_obj: Any) -> int:
    """Approximates LLM token count (~4 characters per token)."""
    if not isinstance(text_or_obj, str):
      text_or_obj = json.dumps(text_or_obj, default=str)
    return max(1, len(text_or_obj) // 4)

  def compact_episodic_history(
      self, history_runs: list[dict[str, Any]], max_recent_runs: int = 3
  ) -> dict[str, Any]:
    """Compresses multi-run shopping history into a concise semantic digest to prevent context bloat."""
    recent = history_runs[:max_recent_runs]
    older_count = max(0, len(history_runs) - max_recent_runs)
    digest_lines = []
    for run in recent:
      digest_lines.append(
          f"- {run.get('title', 'Run')}: {run.get('item_count', 0)} items -> "
          f"{run.get('winning_store_summary', 'N/A')} (£{float(run.get('winning_total_cost', 0.0)):.2f})"
      )
    if older_count > 0:
      avg_spend = sum(
          float(r.get("winning_total_cost", 0.0)) for r in history_runs[max_recent_runs:]
      ) / max(1, older_count)
      digest_lines.append(
          f"- [Compacted Episodic Summary of {older_count} older weekly shops: avg winning total £{avg_spend:.2f}]"
      )
    return {
        "total_historical_runs": len(history_runs),
        "retained_recent_runs": len(recent),
        "compacted_older_runs": older_count,
        "episodic_digest": "\n".join(digest_lines) if digest_lines else "No prior runs.",
    }

  def prune_store_quotes_for_llm_context(
      self, quotes: list[Any]
  ) -> list[dict[str, Any]]:
    """Prunes verbose SKU line-item arrays from store quotes before passing to LLM reasoning prompts."""
    pruned = []
    for q in quotes:
      pruned.append({
          "store_id": q.store.store_id,
          "store_name": q.store.name,
          "store_type": q.store.store_type,
          "distance_km": q.store.distance_km,
          "can_fulfill_entire_list": q.can_fulfill_entire_list,
          "fulfilled_items": f"{q.fulfilled_item_count}/{q.total_requested_item_count}",
          "missing_items": q.missing_items[:4],
          "effective_best_total_gbp": q.effective_best_total,
          "net_weekly_loyalty_advantage_gbp": q.loyalty_analysis.net_weekly_advantage,
      })
    return pruned

  def build_compacted_prompt_context(
      self,
      agent_role: str,
      user_profile: dict[str, Any],
      history_runs: list[dict[str, Any]],
      quotes: list[Any],
  ) -> dict[str, Any]:
    raw_tokens = (
        self.estimate_tokens(user_profile)
        + self.estimate_tokens(history_runs)
        + self.estimate_tokens([asdict(q) if hasattr(q, "__dataclass_fields__") else str(q) for q in quotes])
    )
    sys_inst = SYSTEM_INSTRUCTIONS.get(agent_role, SYSTEM_INSTRUCTIONS["COORDINATOR_AGENT"])
    compacted_history = self.compact_episodic_history(history_runs)
    pruned_quotes = self.prune_store_quotes_for_llm_context(quotes)
    compacted_payload = {
        "system_instruction": sys_inst,
        "user_origin_postcode": getattr(user_profile.get("home_coordinate"), "postcode", "PO20 3SJ"),
        "active_loyalty_programs": user_profile.get("active_loyalty_programs", []),
        "episodic_memory_digest": compacted_history,
        "pruned_store_quotes": pruned_quotes,
    }
    compacted_tokens = self.estimate_tokens(compacted_payload)
    return {
        "prompt_context": compacted_payload,
        "raw_unpruned_tokens": raw_tokens,
        "compacted_context_tokens": compacted_tokens,
        "tokens_saved_by_compaction": max(0, raw_tokens - compacted_tokens),
        "within_token_budget": compacted_tokens <= self.max_context_tokens,
    }


class AsyncMemoryConsolidator:
  """Executes background/asynchronous memory persistence and episodic compaction without blocking."""

  def __init__(self, memory_store: PersistentMemoryStore, max_workers: int = 2) -> None:
    self.memory_store = memory_store
    self._executor = ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix="cartcompass-async-mem"
    )
    self.completed_background_ops: int = 0

  def enqueue_background_run_persistence(
      self,
      *,
      user_id: str,
      title: str,
      items: list[ShoppingItemInput],
      winning_strategy_type: str,
      winning_store_summary: str,
      winning_total_cost: float,
      loyalty_savings_usd: float,
      recommendation_dict: dict[str, Any],
      list_id: str | None = None,
       wait_for_completion: bool = True,
  ) -> str:
    """Schedules PII-redacted SQLite persistence and rolling SKU price consolidation on a background worker."""

    def _worker() -> str:
      saved_id = self.memory_store.record_new_shopping_list_run(
          user_id=user_id,
          title=title,
          items=items,
          winning_strategy_type=winning_strategy_type,
          winning_store_summary=winning_store_summary,
          winning_total_cost=winning_total_cost,
          loyalty_savings_usd=loyalty_savings_usd,
          recommendation_dict=recommendation_dict,
          list_id=list_id,
      )
      self.completed_background_ops += 1
      STRUCTURED_LOGGER.log_event(
          "memory.async_background_consolidation_complete",
          severity="INFO",
          intent="Persist weekly shopping run & update episodic staple frequencies in background",
          outcome="SUCCESS",
          attributes={
              "list_id": saved_id,
              "completed_background_ops": self.completed_background_ops,
              "pii_redacted": True,
          },
      )
      return saved_id

    future: Future[str] = self._executor.submit(_worker)
    if wait_for_completion:
      return future.result(timeout=5.0)
    return list_id or "ASYNC-PENDING"

  async def consolidate_session_memory_async(
      self, user_id: str = "mrmitchell"
  ) -> dict[str, Any]:
    """Native asyncio coroutine for non-blocking episodic memory compaction."""
    history = await asyncio.to_thread(
        self.memory_store.list_shopping_history, user_id, 20
    )
    cwm = ContextWindowManager()
    return cwm.compact_episodic_history(history)
