"""Dedicated Golden Dataset Agent Evaluation Harness for CartCompass UK."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from typing import Any

from cartcompass.agent_adk import (
    GuardrailViolationError,
)
from cartcompass.memory_store import (
    PersistentMemoryStore,
)
from cartcompass.orchestrator import (
    GroceryOptimizationOrchestrator,
)
from cartcompass.tools import (
    execute_tool_with_llm_guidance,
)


def load_golden_dataset(dataset_path: str | None = None) -> dict[str, Any]:
  if dataset_path is None:
    dataset_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "golden_dataset.json"
    )
  with open(dataset_path, "r", encoding="utf-8") as f:
    return json.load(f)


def evaluate_single_golden_case(
    case: dict[str, Any], orchestrator: GroceryOptimizationOrchestrator
) -> dict[str, Any]:
  case_id = case["case_id"]
  case_type = case["type"]
  expected = case["expected"]
  t0 = time.perf_counter()
  checks: list[dict[str, Any]] = []

  def record_check(name: str, passed: bool, detail: str = "") -> None:
    checks.append({"check": name, "passed": bool(passed), "detail": detail})

  try:
    if case_type == "end_to_end_optimization":
      rec = orchestrator.execute_weekly_shopping_run(
          pasted_list_text=case["pasted_list_text"],
          shopping_list_title=case["name"],
          postcode=case.get("postcode", "PO20 3SJ"),
          radius_km=float(case.get("radius_km", 20.0)),
          persist_run=True,
      )
      if "postcode" in expected:
        record_check(
            "postcode_match",
            rec.user_location.postcode == expected["postcode"],
            f"actual={rec.user_location.postcode}",
        )
      if "location_label_contains" in expected:
        record_check(
            "location_label_contains",
            expected["location_label_contains"] in rec.user_location.label,
            f"label={rec.user_location.label}",
        )
      if "best_single_can_fulfill_all" in expected:
        record_check(
            "best_single_can_fulfill_all",
            rec.best_single_store.can_fulfill_entire_list
            is expected["best_single_can_fulfill_all"],
        )
      if "best_single_store_type" in expected:
        record_check(
            "best_single_store_type",
            rec.best_single_store.store.store_type
            == expected["best_single_store_type"],
        )
      if "online_shops_can_fulfill_all" in expected:
        all_online_full = all(
            a["can_fulfill_entire_list"] for a in rec.online_validity_audit
        )
        record_check(
            "online_shops_can_fulfill_all",
            all_online_full is expected["online_shops_can_fulfill_all"],
        )
      if "online_hybrid_plan_required" in expected:
        has_hybrid = rec.online_hybrid_plan is not None
        record_check(
            "online_hybrid_plan_required",
            has_hybrid is expected["online_hybrid_plan_required"],
        )
        if has_hybrid and rec.online_hybrid_plan:
          if "online_hybrid_plan_type" in expected:
            record_check(
                "online_hybrid_plan_type",
                rec.online_hybrid_plan.plan_type
                == expected["online_hybrid_plan_type"],
            )
          if "online_assigned_item_count" in expected:
            record_check(
                "online_assigned_item_count",
                len(rec.online_hybrid_plan.stores[0].assigned_items)
                == expected["online_assigned_item_count"],
            )
          if "regular_assigned_item_count" in expected:
            record_check(
                "regular_assigned_item_count",
                len(rec.online_hybrid_plan.stores[1].assigned_items)
                == expected["regular_assigned_item_count"],
            )
      if "active_chains_zero_weekly_fee" in expected:
        by_chain = {q.store.chain: q for q in rec.ranked_single_stores}
        for ch in expected["active_chains_zero_weekly_fee"]:
          q = by_chain.get(ch)
          record_check(
              f"active_loyalty_{ch}",
              q is not None
              and q.loyalty_analysis.user_already_member
              and q.loyalty_analysis.amortized_weekly_fee == 0.0,
          )

    elif case_type == "tool_error_recovery":
      env = execute_tool_with_llm_guidance(
          case["tool_name"], **case.get("arguments", {})
      )
      record_check("status_is_error", env.status == expected["status"])
      record_check(
          "error_code_matches", env.error_code == expected["error_code"]
      )
      record_check("retriable_matches", env.retriable is expected["retriable"])
      record_check(
          "llm_recovery_instructions_present",
          expected["recovery_contains"] in (env.llm_recovery_instructions or ""),
      )

    elif case_type == "guardrail_block":
      blocked = False
      violation_code = ""
      try:
        orchestrator.execute_weekly_shopping_run(
            pasted_list_text=case["pasted_list_text"],
            shopping_list_title=case["name"],
            persist_run=False,
        )
      except GuardrailViolationError as gve:
        blocked = True
        violation_code = gve.violation_code
      record_check("guardrail_blocked_input", blocked)
      record_check(
          "violation_code_matches",
          violation_code == expected["violation_code"],
          f"violation_code={violation_code}",
      )

    elif case_type == "hitl_workflow":
      rec = orchestrator.execute_weekly_shopping_run(
          pasted_list_text=case["pasted_list_text"],
          shopping_list_title=case["name"],
          postcode=case.get("postcode", "PO20 3SJ"),
          hitl_spend_threshold_gbp=float(
              case.get("hitl_spend_threshold_gbp", 25.0)
          ),
          persist_run=False,
      )
      req_id = rec.hitl_checkpoint.get("request_id", "")
      record_check(
          "initial_hitl_status",
          rec.hitl_checkpoint.get("status") == expected["initial_hitl_status"],
      )
      resolved = orchestrator.hitl_gate.resolve_hitl_request(
          req_id, approved=True, reviewer_note="Approved by golden eval harness"
      )
      record_check(
          "resolved_hitl_status",
          resolved.get("hitl_checkpoint", {}).get("status")
          == expected["resolved_hitl_status"],
      )

    elif case_type == "pii_redaction":
      rec = orchestrator.execute_weekly_shopping_run(
          pasted_list_text=case["pasted_list_text"],
          shopping_list_title=case["shopping_list_title"],
          persist_run=True,
      )
      detail = orchestrator.memory.get_shopping_list_detail(
          rec.shopping_list_id
      )
      serialized_memory = json.dumps(detail)
      serialized_trace = json.dumps(rec.trace_summary)
      for forbidden in expected["must_not_contain"]:
        record_check(
            f"redacted_from_sqlite_{forbidden[:10]}",
            forbidden not in serialized_memory,
        )
        record_check(
            f"redacted_from_logs_{forbidden[:10]}",
            forbidden not in serialized_trace,
        )

  except Exception as exc:
    record_check("unhandled_exception", False, str(exc))

  latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
  case_passed = bool(checks) and all(c["passed"] for c in checks)
  return {
      "case_id": case_id,
      "name": case["name"],
      "type": case_type,
      "passed": case_passed,
      "latency_ms": latency_ms,
      "checks": checks,
  }


def run_golden_evaluation_suite(
    dataset_path: str | None = None,
    output_report_path: str | None = None,
) -> dict[str, Any]:
  dataset = load_golden_dataset(dataset_path)
  with tempfile.TemporaryDirectory() as tmp_dir:
    db_path = os.path.join(tmp_dir, "eval_golden.sqlite3")
    memory = PersistentMemoryStore(db_path=db_path)
    orchestrator = GroceryOptimizationOrchestrator(memory_store=memory)

    case_results = [
        evaluate_single_golden_case(case, orchestrator)
        for case in dataset["cases"]
    ]

  total_cases = len(case_results)
  passed_cases = sum(1 for r in case_results if r["passed"])
  pass_rate = round(passed_cases / max(1, total_cases), 4)
  min_pass_rate = float(dataset.get("minimum_pass_rate", 0.95))

  report = {
      "dataset_name": dataset["dataset_name"],
      "version": dataset["version"],
      "total_cases": total_cases,
      "passed_cases": passed_cases,
      "failed_cases": total_cases - passed_cases,
      "pass_rate": pass_rate,
      "minimum_pass_rate_required": min_pass_rate,
      "suite_passed": pass_rate >= min_pass_rate,
      "results": case_results,
  }

  if output_report_path:
    with open(output_report_path, "w", encoding="utf-8") as f:
      json.dump(report, f, indent=2)

  return report


def main() -> None:
  parser = argparse.ArgumentParser(
      description="Run CartCompass UK Golden Dataset Agent Evaluation Harness."
  )
  parser.add_argument(
      "--output",
      default="",
      help="Optional file path to write JSON evaluation report.",
  )
  args = parser.parse_args()
  report = run_golden_evaluation_suite(
      output_report_path=args.output if args.output else None
  )
  print(
      f"Golden Evaluation Suite: {report['passed_cases']}/{report['total_cases']} "
      f"({report['pass_rate']*100:.1f}%) — {'PASSED' if report['suite_passed'] else 'FAILED'}"
  )
  for r in report["results"]:
    status = "PASS" if r["passed"] else "FAIL"
    print(f"  [{status}] {r['case_id']}: {r['name']} ({r['latency_ms']} ms)")
  if not report["suite_passed"]:
    raise SystemExit(1)


if __name__ == "__main__":
  main()
