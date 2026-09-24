"""Google ADK Multi-Agent Orchestration, Dynamic Model Routing, Guardrails, and Human-in-the-Loop (HITL) Engine."""

from __future__ import annotations

import datetime
import re
from typing import Any, Callable
import uuid

from cartcompass.memory_store import (
    ContextWindowManager,
    SYSTEM_INSTRUCTIONS,
)
from cartcompass.models import (
    HITLApprovalRequest,
    OptimizationRecommendation,
    StoreBasketQuote,
)
from cartcompass.observability import (
    GLOBAL_PII_REDACTOR,
    STRUCTURED_LOGGER,
    TraceRecorder,
)
from cartcompass.secret_manager import (
    GLOBAL_SECRET_MANAGER,
)
from cartcompass.tools import (
    TOOL_DECLARATIONS,
    execute_tool_with_llm_guidance,
)

# Attempt to import Google ADK & Google GenAI SDKs; provide compatible ADK primitives when running offline/CI.
try:
  from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent  # type: ignore
  from google.adk.tools import FunctionTool  # type: ignore
  ADK_NATIVE_AVAILABLE = True
except ImportError:
  ADK_NATIVE_AVAILABLE = False

  class FunctionTool:  # type: ignore
    """ADK-compatible FunctionTool wrapper."""

    def __init__(self, func: Callable[..., Any], name: str | None = None, description: str | None = None) -> None:
      self.func = func
      self.name = name or getattr(func, "__name__", "tool")
      self.description = description or getattr(func, "__doc__", "")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
      return self.func(*args, **kwargs)

  class LlmAgent:  # type: ignore
    """ADK-compatible LlmAgent definition."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        instruction: str,
        description: str = "",
        tools: list[Any] | None = None,
        output_key: str | None = None,
    ) -> None:
      self.name = name
      self.model = model
      self.instruction = instruction
      self.description = description
      self.tools = tools or []
      self.output_key = output_key

  class ParallelAgent:  # type: ignore
    """ADK-compatible ParallelAgent orchestrator."""

    def __init__(
        self,
        *,
        name: str,
        sub_agents: list[Any],
        description: str = "",
    ) -> None:
      self.name = name
      self.sub_agents = sub_agents
      self.description = description

  class SequentialAgent:  # type: ignore
    """ADK-compatible SequentialAgent orchestrator."""

    def __init__(
        self,
        *,
        name: str,
        sub_agents: list[Any],
        description: str = "",
    ) -> None:
      self.name = name
      self.sub_agents = sub_agents
      self.description = description

genai: Any = None
try:
  from google import genai as _genai_mod  # type: ignore

  genai = _genai_mod
  GENAI_SDK_AVAILABLE = True
except ImportError:
  GENAI_SDK_AVAILABLE = False


# ---------------------------------------------------------------------------
# 1. Dynamic Model Router (Flash vs Pro Cost/Latency/Complexity Tiering)
# ---------------------------------------------------------------------------
class ModelRouter:
  """Routes sub-agent tasks between fast extraction (`gemini-2.5-flash`) and deep reasoning (`gemini-2.5-pro`)."""

  FAST_MODEL = "gemini-2.5-flash"
  REASONING_MODEL = "gemini-2.5-pro"

  def __init__(self) -> None:
    self.routing_history: list[dict[str, Any]] = []
    self._api_key = GLOBAL_SECRET_MANAGER.get_secret("GEMINI_API_KEY")
    self._genai_client: Any = None
    if (
        GENAI_SDK_AVAILABLE
        and genai is not None
        and self._api_key
        and not self._api_key.startswith("ephemeral-sm-")
    ):
      try:
        self._genai_client = genai.Client(api_key=self._api_key)
      except Exception:
        self._genai_client = None

  def route_task(
      self,
      *,
      task_name: str,
      agent_name: str,
      complexity_tier: str,
      estimated_prompt_tokens: int,
      requires_multi_store_tradeoff: bool = False,
  ) -> dict[str, Any]:
    """Selects the optimal Gemini model tier based on task complexity and multi-store constraints."""
    if requires_multi_store_tradeoff or complexity_tier in ("HIGH", "MULTI_CONSTRAINT_REASONING"):
      selected_model = self.REASONING_MODEL
      rationale = (
          "Routed to high-reasoning tier (`gemini-2.5-pro`) for multi-constraint GBP (£) "
          "loyalty breakeven & Online + 20km Regular Supermarket split-basket optimization."
      )
    else:
      selected_model = self.FAST_MODEL
      rationale = (
          "Routed to low-latency tier (`gemini-2.5-flash`) for structured UK grocery "
          "item extraction, unit normalization, and postcode geospatial lookup."
      )

    decision = {
        "task_name": task_name,
        "agent_name": agent_name,
        "complexity_tier": complexity_tier,
        "selected_model": selected_model,
        "fallback_model": self.FAST_MODEL,
        "estimated_prompt_tokens": estimated_prompt_tokens,
        "routing_rationale": rationale,
        "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    self.routing_history.append(decision)
    STRUCTURED_LOGGER.log_event(
        "model_router.decision",
        severity="INFO",
        agent_name=agent_name,
        model_id=selected_model,
        intent=f"Route {task_name}",
        outcome="ROUTED",
        attributes=decision,
    )
    return decision

  def generate_executive_advice(
      self,
      *,
      compacted_context: dict[str, Any],
      deterministic_draft_summary: str,
      tracer: TraceRecorder,
  ) -> str:
    """Invokes Gemini (`gemini-2.5-pro`) when configured, with guaranteed fallback to verified GBP synthesis."""
    decision = self.route_task(
        task_name="synthesize_executive_grocery_recommendation",
        agent_name="HybridSplitPlannerSubAgent",
        complexity_tier="MULTI_CONSTRAINT_REASONING",
        estimated_prompt_tokens=compacted_context.get("compacted_context_tokens", 450),
        requires_multi_store_tradeoff=True,
    )
    with tracer.start_span(
        "llm.generate_executive_advice",
        agent_name="HybridSplitPlannerSubAgent",
        model_id=decision["selected_model"],
        compacted_tokens=compacted_context.get("compacted_context_tokens", 0),
        tokens_saved=compacted_context.get("tokens_saved_by_compaction", 0),
    ) as llm_span:
      if self._genai_client is not None:
        try:
          prompt = (
              f"{SYSTEM_INSTRUCTIONS['COORDINATOR_AGENT']}\n\n"
              f"Compacted Context: {compacted_context['prompt_context']}\n\n"
              f"Verified Calculation Summary: {deterministic_draft_summary}\n"
              "Produce a concise 2-sentence UK shopper recommendation in GBP (£) preserving exact figures."
          )
          resp = self._genai_client.models.generate_content(
              model=decision["selected_model"],
              contents=prompt,
          )
          text = getattr(resp, "text", None)
          if text and "£" in text:
            llm_span.set_attribute("llm.execution_mode", "live_gemini_api")
            return GLOBAL_PII_REDACTOR.redact_text(text.strip())
        except Exception as exc:
          llm_span.set_attribute("llm.fallback_reason", str(exc))

      llm_span.set_attribute(
          "llm.execution_mode", "verified_adk_grounded_synthesis"
      )
      return GLOBAL_PII_REDACTOR.redact_text(deterministic_draft_summary)


# ---------------------------------------------------------------------------
# 2. Input & Output Guardrails (Prompt Injection, Domain Safety, Hallucination)
# ---------------------------------------------------------------------------
class GuardrailViolationError(ValueError):
  """Raised when an input prompt injection or domain safety guardrail is violated."""

  def __init__(
      self,
      *,
      guardrail_name: str,
      violation_code: str,
      message: str,
      llm_recovery_instructions: str,
  ) -> None:
    super().__init__(message)
    self.guardrail_name = guardrail_name
    self.violation_code = violation_code
    self.message = message
    self.llm_recovery_instructions = llm_recovery_instructions


class SafetyAndDomainGuardrails:
  """Enforces Input Guardrails (prompt injection, PII scrubbing, UK bounds) and Output Guardrails (anti-hallucination)."""

  _PROMPT_INJECTION_PATTERNS = re.compile(
      r"(?:ignore\s+(?:all\s+)?previous\s+instructions|system\s+prompt|reveal\s+your\s+instructions|"
      r"you\s+are\s+now\s+dan|drop\s+table\s+|;\s*delete\s+from|<script\b)",
      re.IGNORECASE,
  )
  _PROHIBITED_NON_GROCERY_PATTERNS = re.compile(
      r"\b(?:explosives?|firearms?|ammunition|cyanide|fentanyl|illegal\s+narcotics)\b",
      re.IGNORECASE,
  )

  def validate_input_guardrails(
      self,
      *,
      pasted_list_text: str | None,
      shopping_list_title: str | None,
      radius_km: float,
      tracer: TraceRecorder,
  ) -> dict[str, Any]:
    """Runs input safety, prompt-injection, PII scrubbing, and geospatial sanity guardrails."""
    with tracer.start_span(
        "guardrail.input_validation",
        agent_name="SafetyAndDomainGuardrails",
    ) as span:
      combined_text = f"{shopping_list_title or ''}\n{pasted_list_text or ''}"

      if self._PROMPT_INJECTION_PATTERNS.search(combined_text):
        span.set_attribute("guardrail.status", "BLOCKED_PROMPT_INJECTION")
        raise GuardrailViolationError(
            guardrail_name="input_prompt_injection_shield",
            violation_code="PROMPT_INJECTION_DETECTED",
            message="Blocked potential prompt injection or instruction-override pattern in shopping list input.",
            llm_recovery_instructions=(
                "Remove meta-instructions (e.g., 'ignore previous instructions') and submit only "
                "valid UK grocery items with quantities and units."
            ),
        )

      if self._PROHIBITED_NON_GROCERY_PATTERNS.search(combined_text):
        span.set_attribute("guardrail.status", "BLOCKED_PROHIBITED_ITEM")
        raise GuardrailViolationError(
            guardrail_name="input_prohibited_item_shield",
            violation_code="PROHIBITED_NON_GROCERY_ITEM",
            message="Input contains prohibited non-grocery or hazardous items.",
            llm_recovery_instructions=(
                "Submit only legal supermarket food, drink, household, or wholefood pantry items."
            ),
        )

      if radius_km <= 0.0 or radius_km > 100.0:
        span.set_attribute("guardrail.status", "BLOCKED_INVALID_RADIUS")
        raise GuardrailViolationError(
            guardrail_name="input_geospatial_radius_bounds",
            violation_code="RADIUS_OUT_OF_GUARDRAIL_BOUNDS",
            message=f"Search radius {radius_km} km violates allowed UK geospatial bounds (0, 100] km.",
            llm_recovery_instructions="Retry with `radius_km=20.0`.",
        )

      sanitized_text = GLOBAL_PII_REDACTOR.redact_text(pasted_list_text or "")
      sanitized_title = GLOBAL_PII_REDACTOR.redact_text(
          shopping_list_title or "Weekly Grocery List"
      )
      verdict = {
          "input_guardrail_passed": True,
          "prompt_injection_checked": True,
          "prohibited_items_checked": True,
          "pii_scrubbed": sanitized_text != (pasted_list_text or ""),
          "sanitized_list_text": sanitized_text,
          "sanitized_title": sanitized_title,
      }
      span.set_attribute("guardrail.status", "PASSED")
      span.set_attribute("guardrail.pii_scrubbed", verdict["pii_scrubbed"])
      return verdict

  def validate_output_guardrails(
      self,
      *,
      best_single: StoreBasketQuote,
      online_hybrid_plan: Any,
      verified_store_ids: set[str],
      executive_summary: str,
      tracer: TraceRecorder,
  ) -> dict[str, Any]:
    """Verifies no hallucinated store IDs, 100% single-store fulfillment integrity, and GBP (£) formatting."""
    with tracer.start_span(
        "guardrail.output_validation",
        agent_name="SafetyAndDomainGuardrails",
    ) as span:
      hallucinated_ids: list[str] = []
      if best_single.store.store_id not in verified_store_ids:
        hallucinated_ids.append(best_single.store.store_id)
      if online_hybrid_plan and hasattr(online_hybrid_plan, "stores"):
        for leg in online_hybrid_plan.stores:
          if leg.store_id not in verified_store_ids:
            hallucinated_ids.append(leg.store_id)

      single_store_fulfillment_valid = bool(best_single.can_fulfill_entire_list)
      currency_gbp_valid = "£" in executive_summary

      verdict = {
          "output_guardrail_passed": (
              len(hallucinated_ids) == 0
              and single_store_fulfillment_valid
              and currency_gbp_valid
          ),
          "hallucinated_store_ids": hallucinated_ids,
          "single_store_100pct_fulfillment_verified": single_store_fulfillment_valid,
          "gbp_currency_verified": currency_gbp_valid,
      }
      span.set_attribute(
          "guardrail.output_passed", verdict["output_guardrail_passed"]
      )
      return verdict


# ---------------------------------------------------------------------------
# 3. Human-in-the-Loop (HITL) Approval Gate
# ---------------------------------------------------------------------------
class HumanInTheLoopGate:
  """Manages HITL approval checkpoints for high-spend baskets or new paid membership enrollments."""

  def __init__(self, default_spend_threshold_gbp: float = 75.0) -> None:
    self.default_spend_threshold_gbp = default_spend_threshold_gbp
    self.pending_requests: dict[str, HITLApprovalRequest] = {}

  def evaluate_hitl_checkpoint(
      self,
      *,
      winning_total_cost_gbp: float,
      best_single: StoreBasketQuote,
      winning_strategy_type: str,
      spend_threshold_gbp: float | None = None,
      tracer: TraceRecorder,
  ) -> HITLApprovalRequest:
    threshold = (
        spend_threshold_gbp
        if spend_threshold_gbp is not None
        else self.default_spend_threshold_gbp
    )
    with tracer.start_span(
        "hitl.evaluate_approval_gate",
        agent_name="HumanInTheLoopGate",
        basket_total_gbp=winning_total_cost_gbp,
        spend_threshold_gbp=threshold,
    ) as span:
      reasons: list[str] = []
      if winning_total_cost_gbp > threshold:
        reasons.append(
            f"Weekly basket total (£{winning_total_cost_gbp:.2f}) exceeds HITL spend threshold (£{threshold:.2f})."
        )
      la = best_single.loyalty_analysis
      if (
          la.is_advantageous
          and not la.user_already_member
          and la.annual_membership_fee > 0
      ):
        reasons.append(
            f"Recommends enrolling in paid membership {la.program_name} (£{la.annual_membership_fee:.2f}/yr)."
        )

      requires_human = len(reasons) > 0
      req = HITLApprovalRequest(
          request_id=f"HITL-{uuid.uuid4().hex[:8].upper()}",
          status=(
              "PENDING_HUMAN_APPROVAL"
              if requires_human
              else "AUTO_APPROVED_BELOW_THRESHOLD"
          ),
          requires_human_confirmation=requires_human,
          trigger_reason=(
              " ".join(reasons)
              if reasons
              else f"Basket total £{winning_total_cost_gbp:.2f} is within the £{threshold:.2f} auto-approval policy and uses existing active UK loyalty memberships."
          ),
          basket_total_gbp=round(winning_total_cost_gbp, 2),
          spend_threshold_gbp=round(threshold, 2),
          recommended_action_summary=(
              f"{winning_strategy_type} via {best_single.store.name} (£{winning_total_cost_gbp:.2f})"
          ),
          created_at_iso=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      )
      self.pending_requests[req.request_id] = req
      span.set_attribute("hitl.status", req.status)
      span.set_attribute(
          "hitl.requires_human_confirmation", req.requires_human_confirmation
      )
      return req

  def resolve_hitl_request(
      self,
      request_id: str,
      *,
      approved: bool,
      reviewer_note: str = "",
  ) -> dict[str, Any]:
    req = self.pending_requests.get(request_id)
    if not req:
      return {
          "status": "error",
          "error_code": "HITL_REQUEST_NOT_FOUND",
          "message": f"HITL request '{request_id}' was not found.",
          "llm_recovery_instructions": "Verify `request_id` from `recommendation.hitl_checkpoint.request_id`.",
      }
    req.status = "APPROVED" if approved else "REJECTED"
    req.requires_human_confirmation = False
    STRUCTURED_LOGGER.log_event(
        "hitl.human_decision_recorded",
        severity="INFO",
        agent_name="HumanInTheLoopGate",
        intent=f"Resolve HITL checkpoint {request_id}",
        outcome=req.status,
        attributes={
            "request_id": request_id,
            "decision": req.status,
            "reviewer_note": GLOBAL_PII_REDACTOR.redact_text(reviewer_note),
        },
    )
    return {"status": "success", "hitl_checkpoint": req.to_dict()}


# ---------------------------------------------------------------------------
# 4. Google ADK Multi-Agent Hierarchy Definition
# ---------------------------------------------------------------------------
def build_cartcompass_adk_agent_hierarchy() -> dict[str, Any]:
  """Constructs the Google ADK Coordinator Agent and Specialist Sub-Agents with FunctionTools."""
  adk_tools = [
      FunctionTool(
          lambda postcode: execute_tool_with_llm_guidance(
              "resolve_uk_postcode", postcode=postcode
          ).to_dict(),
          name="resolve_uk_postcode",
          description=TOOL_DECLARATIONS[0]["description"],
      ),
      FunctionTool(
          lambda raw_text: execute_tool_with_llm_guidance(
              "parse_pasted_grocery_list", raw_text=raw_text
          ).to_dict(),
          name="parse_pasted_grocery_list",
          description=TOOL_DECLARATIONS[1]["description"],
      ),
      FunctionTool(
          lambda latitude, longitude, radius_km=20.0, include_online_shops=True: execute_tool_with_llm_guidance(
              "discover_stores_within_radius",
              latitude=latitude,
              longitude=longitude,
              radius_km=radius_km,
              include_online_shops=include_online_shops,
          ).to_dict(),
          name="discover_stores_within_radius",
          description=TOOL_DECLARATIONS[2]["description"],
      ),
  ]

  list_parser_agent = LlmAgent(
      name="ListParserSubAgent",
      model=ModelRouter.FAST_MODEL,
      instruction=SYSTEM_INSTRUCTIONS["LIST_PARSER_SUB_AGENT"],
      description="Parses pasted UK shopping lists and classifies AMBIENT_WHOLEFOOD vs FRESH_CHILLED items.",
      tools=[adk_tools[1]],
      output_key="parsed_shopping_items",
  )

  geospatial_discovery_agent = LlmAgent(
      name="GeospatialDiscoverySubAgent",
      model=ModelRouter.FAST_MODEL,
      instruction=SYSTEM_INSTRUCTIONS["GEOSPATIAL_DISCOVERY_SUB_AGENT"],
      description="Resolves UK postcodes and discovers supermarkets within 20.0 km + UK online retailers.",
      tools=[adk_tools[0], adk_tools[2]],
      output_key="discovered_uk_stores",
  )

  pricing_and_loyalty_agent = LlmAgent(
      name="PricingAndLoyaltySubAgent",
      model=ModelRouter.REASONING_MODEL,
      instruction=SYSTEM_INSTRUCTIONS["PRICING_AND_LOYALTY_SUB_AGENT"],
      description="Audits online shop basket validity and calculates GBP (£) loyalty ROI across 8 retailers.",
      tools=adk_tools,
      output_key="store_quotes_and_validity_audit",
  )

  parallel_evaluation_group = ParallelAgent(
      name="ParallelStorePricingAndLoyaltyGroup",
      sub_agents=[pricing_and_loyalty_agent],
      description="Executes store catalog quotes and loyalty ROI analysis concurrently.",
  )

  hybrid_split_planner_agent = LlmAgent(
      name="HybridSplitPlannerSubAgent",
      model=ModelRouter.REASONING_MODEL,
      instruction=SYSTEM_INSTRUCTIONS["HYBRID_SPLIT_PLANNER_SUB_AGENT"],
      description="Generates the 2-step Online Wholefood + Regular 20km Supermarket split-purchase plan.",
      tools=adk_tools,
      output_key="final_optimization_recommendation",
  )

  coordinator_agent = SequentialAgent(
      name="CartCompassCoordinatorAgent",
      sub_agents=[
          list_parser_agent,
          geospatial_discovery_agent,
          parallel_evaluation_group,
          hybrid_split_planner_agent,
      ],
      description="Root Google ADK Sequential Coordinator orchestrating UK 20km & Online Grocery Optimization.",
  )

  return {
      "adk_native_available": ADK_NATIVE_AVAILABLE,
      "genai_sdk_available": GENAI_SDK_AVAILABLE,
      "root_agent": coordinator_agent,
      "sub_agents": [
          list_parser_agent,
          geospatial_discovery_agent,
          parallel_evaluation_group,
          hybrid_split_planner_agent,
      ],
  }


GLOBAL_HITL_GATE = HumanInTheLoopGate(default_spend_threshold_gbp=75.0)
GLOBAL_GUARDRAILS = SafetyAndDomainGuardrails()
GLOBAL_MODEL_ROUTER = ModelRouter()
