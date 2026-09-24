"""HTTP Server, REST API, and CLI Entrypoint for the Eastergate (20km) UK Grocery Optimizer (GBP £)."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from typing import Any
from urllib.parse import urlparse

from cartcompass.memory_store import DEFAULT_UK_LOYALTY_PROGRAMS, PersistentMemoryStore
from cartcompass.models import GeoCoordinate, ShoppingItemInput
from cartcompass.orchestrator import GroceryOptimizationOrchestrator
from cartcompass.tools import (
    TOOL_DECLARATIONS,
    discover_stores_within_radius,
    parse_pasted_grocery_list,
    resolve_uk_postcode,
)
from cartcompass.ui_template import HTML_UI_PAGE


def ensure_baseline_history(orchestrator: GroceryOptimizationOrchestrator) -> None:
  """Seeds one prior weekly run if history is empty so multi-run comparison works immediately."""
  existing = orchestrator.memory.list_shopping_history(user_id="mrmitchell")
  if not existing:
    prior_pasted_text = "\n".join([
        "1x British Semi-Skimmed Milk 2L",
        "1 dozen British Free-Range Large Eggs",
        "1 Artisan White Sourdough Bloomer",
        "1kg Sussex Braeburn Apples",
        "1 pack Almonds, Walnuts & Chia Seeds",
        "2 packs Italian Durum Wheat Penne Pasta",
    ])
    orchestrator.execute_weekly_shopping_run(
        pasted_list_text=prior_pasted_text,
        shopping_list_title="Week of 16 Sep — Baseline Eastergate Weekly Shop",
        user_id="mrmitchell",
        persist_run=True,
    )


def create_request_handler(orchestrator: GroceryOptimizationOrchestrator):
  """Creates an HTTP request handler bound to the orchestrator and persistent memory store."""

  class GroceryAppRequestHandler(BaseHTTPRequestHandler):

    def _send_json(
        self, payload: dict[str, Any], status: int = HTTPStatus.OK
    ) -> None:
      body = json.dumps(payload, indent=2).encode("utf-8")
      self.send_response(status)
      self.send_header("Content-Type", "application/json; charset=utf-8")
      self.send_header("Content-Length", str(len(body)))
      self.send_header("Cache-Control", "no-store")
      self.end_headers()
      self.wfile.write(body)

    def _send_html(self, html_content: str) -> None:
      body = html_content.encode("utf-8")
      self.send_response(HTTPStatus.OK)
      self.send_header("Content-Type", "text/html; charset=utf-8")
      self.send_header("Content-Length", str(len(body)))
      self.end_headers()
      self.wfile.write(body)

    def log_message(self, format_str: str, *args: Any) -> None:
      sys.stderr.write(f"[HTTP] {self.address_string()} - {format_str % args}\n")

    def do_GET(self) -> None:  # pylint: disable=invalid-name
      parsed = urlparse(self.path)
      if parsed.path in ("/", "/index.html"):
        self._send_html(HTML_UI_PAGE)
        return

      if parsed.path == "/healthz":
        self._send_json({
            "status": "SERVING",
            "service": "grocery-price-optimization-app-uk",
            "currency": "GBP",
            "default_home": "Eastergate, West Sussex, UK (PO20 3SJ — 50.845561, -0.643677)",
            "radius_limit_km": 20.0,
            "default_loyalty_memberships": DEFAULT_UK_LOYALTY_PROGRAMS,
            "memory_db_path": orchestrator.memory.db_path,
        })
        return

      if parsed.path == "/api/tools":
        self._send_json({"tools": TOOL_DECLARATIONS})
        return

      if parsed.path == "/api/history":
        history = orchestrator.memory.list_shopping_history(user_id="mrmitchell")
        staples = orchestrator.memory.get_frequent_staples(user_id="mrmitchell")
        profile = orchestrator.memory.get_user_profile(user_id="mrmitchell")
        self._send_json({
            "user_profile": {
                "user_id": profile["user_id"],
                "latitude": profile["home_coordinate"].latitude,
                "longitude": profile["home_coordinate"].longitude,
                "label": profile["home_coordinate"].label,
                "postcode": getattr(profile["home_coordinate"], "postcode", "PO20 3SJ"),
                "default_radius_km": profile["default_radius_km"],
                "active_loyalty_programs": profile["active_loyalty_programs"],
            },
            "history": history,
            "frequent_staples": staples,
        })
        return

      self._send_json(
          {"error": f"Route not found: {parsed.path}"},
          status=HTTPStatus.NOT_FOUND,
      )

    def do_POST(self) -> None:  # pylint: disable=invalid-name
      parsed = urlparse(self.path)
      if parsed.path == "/api/postcode":
        try:
          length = int(self.headers.get("Content-Length", "0"))
          raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
          data = json.loads(raw_body)
          raw_pc = str(data.get("postcode", "PO20 3SJ")).strip()
          radius_km = float(data.get("radius_km", 20.0))
          resolved = resolve_uk_postcode(raw_pc)
          orchestrator.memory.update_user_profile(
              user_id="mrmitchell",
              latitude=resolved.latitude,
              longitude=resolved.longitude,
              home_label=resolved.label,
              default_radius_km=radius_km,
          )
          stores_in, stores_out = discover_stores_within_radius(
              user_location=resolved,
              radius_km=radius_km,
              include_online_shops=True,
          )
          self._send_json({
              "resolved_location": {
                  "postcode": resolved.postcode,
                  "latitude": resolved.latitude,
                  "longitude": resolved.longitude,
                  "label": resolved.label,
                  "radius_km": radius_km,
              },
              "stores_within_radius": [
                  {
                      "store_id": s.store_id,
                      "name": s.name,
                      "chain": s.chain,
                      "distance_km": s.distance_km,
                      "store_type": s.store_type,
                      "catalog_scope": s.catalog_scope,
                  }
                  for s in stores_in
              ],
              "stores_excluded_outside_radius": [
                  {
                      "store_id": s.store_id,
                      "name": s.name,
                      "distance_km": s.distance_km,
                  }
                  for s in stores_out
              ],
          })
        except Exception as exc:  # pylint: disable=broad-exception-caught
          self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        return

      if parsed.path == "/api/optimize":
        try:
          length = int(self.headers.get("Content-Length", "0"))
          raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
          data = json.loads(raw_body)

          pasted_list_text = str(data.get("pasted_list_text", "")).strip()
          raw_items = data.get("items") or []
          items: list[ShoppingItemInput] = []
          if pasted_list_text:
            items = parse_pasted_grocery_list(pasted_list_text)
          elif raw_items:
            items = [
                ShoppingItemInput(
                    name=str(it.get("name", "")),
                    quantity=float(it.get("quantity", 1.0)),
                    unit=str(it.get("unit", "count")),
                )
                for it in raw_items
                if str(it.get("name", "")).strip()
            ]

          postcode_str = str(data.get("postcode", "")).strip()
          if postcode_str:
            resolved_coord = resolve_uk_postcode(postcode_str)
            lat = float(data.get("latitude", resolved_coord.latitude))
            lon = float(data.get("longitude", resolved_coord.longitude))
            loc_label = str(data.get("label", resolved_coord.label))
            resolved_pc = resolved_coord.postcode
          else:
            lat = float(data.get("latitude", 50.845561))
            lon = float(data.get("longitude", -0.643677))
            loc_label = str(
                data.get("label", "Home (Eastergate, West Sussex, UK)")
            )
            resolved_pc = "PO20 3SJ"

          radius_km = float(data.get("radius_km", 20.0))
          title = str(data.get("title", "New Weekly Grocery List"))
          active_programs = data.get("active_loyalty_programs")
          persist_run = bool(data.get("persist_run", True))
          include_online_shops = bool(data.get("include_online_shops", True))

          if active_programs is not None or postcode_str:
            orchestrator.memory.update_user_profile(
                user_id="mrmitchell",
                latitude=lat,
                longitude=lon,
                home_label=loc_label,
                active_loyalty_programs=(
                    list(active_programs) if active_programs is not None else None
                ),
                default_radius_km=radius_km,
            )

          rec = orchestrator.execute_weekly_shopping_run(
              items=items,
              pasted_list_text=pasted_list_text if pasted_list_text else None,
              shopping_list_title=title,
              user_id="mrmitchell",
              override_location=GeoCoordinate(
                  latitude=lat,
                  longitude=lon,
                  label=loc_label,
                  postcode=resolved_pc,
              ),
              postcode=postcode_str if postcode_str else None,
              radius_km=radius_km,
              override_loyalty_programs=active_programs,
              persist_run=persist_run,
              include_online_shops=include_online_shops,
          )

          history = orchestrator.memory.list_shopping_history(user_id="mrmitchell")
          staples = orchestrator.memory.get_frequent_staples(user_id="mrmitchell")
          self._send_json({
              "recommendation": rec.to_dict(),
              "history": history,
              "frequent_staples": staples,
          })
        except Exception as exc:  # pylint: disable=broad-exception-caught
          self._send_json(
              {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST
          )
        return

      self._send_json(
          {"error": f"Unsupported POST endpoint: {parsed.path}"},
          status=HTTPStatus.NOT_FOUND,
      )

  return GroceryAppRequestHandler


def format_cli_report(rec_dict: dict[str, Any], history_count: int) -> str:
  """Formats a structured terminal report in GBP (£) for CLI execution."""
  lines = []
  lines.append("=" * 92)
  lines.append(
      f" CARTCOMPASS UK (20KM + ONLINE VALIDITY) — GROCERY & LOYALTY REPORT ({rec_dict['run_id']})"
  )
  lines.append("=" * 92)
  lines.append(
      f" Shopping List Title : {rec_dict['shopping_list_title']} ({rec_dict['shopping_list_id']})"
  )
  loc = rec_dict["user_location"]
  pc = loc.get("postcode", "PO20 3SJ")
  lines.append(
      f" UK Postcode & Rad   : {pc} — {loc['label']} ({loc['latitude']}, {loc['longitude']}) | <= {rec_dict['search_radius_km']} km"
  )
  lines.append(
      f" Stores Evaluated    : {rec_dict['stores_within_radius_count']} total (5 physical <=20km + 3 UK online) | {len(rec_dict['stores_excluded_outside_radius'])} excluded (>20km)"
  )
  lines.append(f" Saved Lists in DB   : {history_count} total weekly runs persisted")

  audit = rec_dict.get("online_validity_audit") or []
  if audit:
    lines.append("-" * 92)
    lines.append(" 1. ONLINE SHOP BASKET VALIDITY CHECK (CAN THEY SUPPORT THE WHOLE LIST?)")
    lines.append("-" * 92)
    for a in audit:
      status_badge = (
          "✓ FULL LIST SUPPORTED"
          if a["can_fulfill_entire_list"]
          else f"✗ PARTIAL ONLY ({a['fulfilled_item_count']}/{a['total_requested_item_count']} items, {a['fulfillment_coverage_pct']}%)"
      )
      lines.append(f" • {a['store_name']} -> {status_badge}")
      lines.append(f"   {a['online_validity_note']}")

  hp = rec_dict.get("online_hybrid_plan") or rec_dict.get("best_split_basket")
  if hp:
    lines.append("-" * 92)
    lines.append(
        " 2. RECOMMENDED SPLIT ACTION: PURCHASE CERTAIN ITEMS ONLINE + REST AT REGULAR 20KM SHOP"
    )
    lines.append("-" * 92)
    lines.append(f" {hp['rationale']}")
    for st_alloc in hp["stores"]:
      item_list_str = ", ".join(
          f"{it['requested_item']} (£{it['loyalty_line_total'] if st_alloc['use_loyalty'] else it['regular_line_total']:.2f})"
          for it in st_alloc["assigned_items"]
      )
      lines.append(
          f"   -> {st_alloc['store_name']} (Subtotal £{st_alloc['subtotal']:.2f}): {item_list_str}"
      )
    if hp.get("free_delivery_tip"):
      lines.append(f"   * {hp['free_delivery_tip']}")

  lines.append("-" * 92)
  lines.append(
      " 3. RANKED SUPERMARKETS (<=20KM FULL LIST) & ONLINE PARTIAL BASKETS (GBP £)"
  )
  lines.append("-" * 92)
  for idx, sq in enumerate(rec_dict["ranked_single_stores"], start=1):
    st = sq["store"]
    la = sq["loyalty_analysis"]
    can_all = sq.get("can_fulfill_entire_list", True)
    marker = (
        "★ 100% LIST WINNER"
        if idx == 1 and can_all
        else (f"  Rank #{idx} (100% List)" if can_all else f"  [PARTIAL {sq['fulfilled_item_count']}/{sq['total_requested_item_count']} ITEMS]")
    )
    dist_str = (
        "ONLINE DELIVERY"
        if st.get("store_type") == "ONLINE_UK"
        else f"{st['distance_km']} km"
    )
    lines.append(
        f" {marker} | {st['name']} ({dist_str}) | Effective Total: £{sq['effective_best_total']:.2f}"
    )
    lines.append(
        f"          Fulfilment      : {sq.get('online_validity_note', 'Full basket')}"
    )
    lines.append(
        f"          Loyalty Verdict : {la['program_name']} -> {'ADVANTAGEOUS' if la['is_advantageous'] else 'NOT ADVANTAGEOUS'} (+£{la['total_weekly_member_benefit']:.2f}/wk)"
    )
    lines.append("")

  lines.append("-" * 92)
  lines.append(" 4. OPENTELEMETRY TRACE & OBSERVABILITY SUMMARY")
  lines.append("-" * 92)
  ts = rec_dict["trace_summary"]
  lines.append(
      f" Trace ID: {rec_dict['trace_id']} | Total Spans: {ts['total_spans']} | Root Latency: {ts['root_duration_ms']} ms"
  )
  lines.append("=" * 92)
  return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
      description="UK Postcode (20km) + Online Validity Weekly Grocery & Loyalty Price Optimizer (GBP £)"
  )
  parser.add_argument(
      "--port", type=int, default=8765, help="Port for Web UI & REST server"
  )
  parser.add_argument(
      "--host", type=str, default="0.0.0.0", help="Host address to bind"
  )
  parser.add_argument(
      "--cli",
      action="store_true",
      help="Run a new pasted shopping list optimization in CLI mode and exit",
  )
  parser.add_argument(
      "--postcode",
      type=str,
      default="PO20 3SJ",
      help="UK Postcode to reset location and run a new 20km search (e.g. 'PO20 3SJ', 'RH12 1HQ', 'BN1 4GQ')",
  )
  parser.add_argument(
      "--title",
      type=str,
      default="Week of 23 Sep — Eastergate Family Weekly Shop",
      help="Title for the new shopping list run",
  )
  parser.add_argument(
      "--paste-list",
      type=str,
      default="",
      help="Multi-line or comma-separated pasted grocery list text",
  )
  parser.add_argument(
      "--items",
      type=str,
      default="2x Semi-Skimmed Milk 2L\n1 dozen Free-Range Large Eggs\n1.5kg British Chicken Breast Fillets\n1 Artisan White Sourdough Bloomer\n1.5kg Sussex Braeburn Apples\n1 pack Almonds, Walnuts & Chia Seeds\n1 pack Rich Roast Arabica Coffee\n1L Extra Virgin Olive Oil\n2 packs Greek Style Natural Yogurt",
      help="Pasted grocery items (newline or comma-separated)",
  )
  parser.add_argument("--lat", type=float, default=50.845561)
  parser.add_argument("--lon", type=float, default=-0.643677)
  parser.add_argument(
      "--label",
      type=str,
      default="Home (Eastergate, West Sussex, UK)",
  )
  parser.add_argument("--radius-km", type=float, default=20.0)
  parser.add_argument("--json", action="store_true", help="Output JSON in CLI mode")
  args = parser.parse_args(argv)

  orchestrator = GroceryOptimizationOrchestrator()
  ensure_baseline_history(orchestrator)

  if args.cli:
    raw_text = args.paste_list.strip() if args.paste_list.strip() else args.items
    rec = orchestrator.execute_weekly_shopping_run(
        pasted_list_text=raw_text,
        shopping_list_title=args.title,
        postcode=args.postcode,
        override_location=GeoCoordinate(
            latitude=args.lat,
            longitude=args.lon,
            label=args.label,
            postcode=args.postcode,
        ),
        radius_km=args.radius_km,
        persist_run=True,
    )
    history = orchestrator.memory.list_shopping_history(user_id="mrmitchell")
    if args.json:
      print(json.dumps(rec.to_dict(), indent=2))
    else:
      print(format_cli_report(rec.to_dict(), len(history)))
    return 0

  handler_cls = create_request_handler(orchestrator)
  server = ThreadingHTTPServer((args.host, args.port), handler_cls)
  print(
      f"CartCompass UK (20km Eastergate) Optimizer running on http://{args.host}:{args.port}",
      flush=True,
  )
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.server_close()
  return 0


if __name__ == "__main__":
  sys.exit(main())
