"""Agentic & Deterministic Pipeline Orchestrator for Weekly UK Grocery Price Optimization (GBP £)."""

from __future__ import annotations

import datetime
from typing import Any
import uuid

from cartcompass.agent_adk import (
    GLOBAL_GUARDRAILS,
    GLOBAL_HITL_GATE,
    GLOBAL_MODEL_ROUTER,
    build_cartcompass_adk_agent_hierarchy,
)
from cartcompass.memory_store import (
    AsyncMemoryConsolidator,
    ContextWindowManager,
    PersistentMemoryStore,
)
from cartcompass.models import (
    GeoCoordinate,
    OptimizationRecommendation,
    ShoppingItemInput,
    StoreBasketQuote,
)
from cartcompass.observability import TraceRecorder
from cartcompass.tools import (
    CANONICAL_CATALOG,
    build_online_plus_regular_shop_plan,
    discover_stores_within_radius,
    execute_tool_with_llm_guidance,
    fetch_store_catalog_quote,
    optimize_split_basket_strategy,
    parse_pasted_grocery_list,
    resolve_uk_postcode,
)


class GroceryOptimizationOrchestrator:
  """Coordinates ADK Multi-Agent workflow, Model Routing, Guardrails, HITL, UK postcode 20km discovery, online validity auditing, GBP pricing, loyalty ROI, and async PII-redacted memory."""

  def __init__(self, memory_store: PersistentMemoryStore | None = None) -> None:
    self.memory = memory_store or PersistentMemoryStore()
    self.adk_hierarchy = build_cartcompass_adk_agent_hierarchy()
    self.model_router = GLOBAL_MODEL_ROUTER
    self.guardrails = GLOBAL_GUARDRAILS
    self.hitl_gate = GLOBAL_HITL_GATE
    self.context_manager = ContextWindowManager()
    self.async_memory = AsyncMemoryConsolidator(self.memory)

  def execute_weekly_shopping_run(
      self,
      items: list[ShoppingItemInput] | None = None,
      pasted_list_text: str | None = None,
      shopping_list_title: str | None = None,
      user_id: str = "mrmitchell",
      override_location: GeoCoordinate | None = None,
      postcode: str | None = None,
      radius_km: float = 20.0,
      override_loyalty_programs: list[str] | None = None,
      include_online_shops: bool = True,
      persist_run: bool = True,
      hitl_spend_threshold_gbp: float = 75.0,
  ) -> OptimizationRecommendation:
    """Executes the full multi-agent ADK grocery optimization pipeline with distributed tracing, guardrails, model routing, and HITL."""
    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    list_id = f"LIST-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tracer = TraceRecorder()
    routing_decisions: list[dict[str, Any]] = []

    with tracer.start_span(
        "orchestrator.execute_weekly_shopping_run",
        run_id=run_id,
        user_id=user_id,
        radius_km=radius_km,
        include_online_shops=include_online_shops,
        currency="GBP",
        agent_name="CartCompassCoordinatorAgent",
    ) as root_span:
      # Stage 0: Input Guardrails (Prompt Injection, Domain Safety, PII Scrubbing)
      input_guardrail_verdict = self.guardrails.validate_input_guardrails(
          pasted_list_text=pasted_list_text,
          shopping_list_title=shopping_list_title,
          radius_km=radius_km,
          tracer=tracer,
      )
      if pasted_list_text:
        pasted_list_text = input_guardrail_verdict["sanitized_list_text"]
      if shopping_list_title:
        shopping_list_title = input_guardrail_verdict["sanitized_title"]

      # Sub-Agent 1 Routing: GeospatialDiscoverySubAgent (gemini-2.5-flash)
      routing_decisions.append(
          self.model_router.route_task(
              task_name="resolve_postcode_and_discover_20km_stores",
              agent_name="GeospatialDiscoverySubAgent",
              complexity_tier="LOW",
              estimated_prompt_tokens=180,
          )
      )
      # Optional Stage 0a: Resolve UK Postcode to reset location & 20km search
      if postcode and postcode.strip():
        with tracer.start_span(
            "tool.resolve_uk_postcode",
            postcode=postcode.strip(),
            agent_name="GeospatialDiscoverySubAgent",
            model_id=self.model_router.FAST_MODEL,
        ) as pc_span:
          pc_env = execute_tool_with_llm_guidance(
              "resolve_uk_postcode", postcode=postcode.strip()
          )
          if pc_env.status == "error":
            pc_span.set_attribute("llm_recovery_triggered", True)
            pc_span.set_attribute(
                "llm_recovery_instructions", pc_env.llm_recovery_instructions
            )
            override_location = resolve_uk_postcode(
                pc_env.suggested_arguments.get("postcode", "PO20 3SJ")
            )
          else:
            override_location = resolve_uk_postcode(postcode.strip())
          pc_span.set_attribute("resolved.latitude", override_location.latitude)
          pc_span.set_attribute("resolved.longitude", override_location.longitude)
          pc_span.set_attribute("resolved.label", override_location.label)
          pc_span.set_attribute("resolved.postcode", override_location.postcode)
          if persist_run:
            self.memory.update_user_profile(
                user_id=user_id,
                latitude=override_location.latitude,
                longitude=override_location.longitude,
                home_label=override_location.label,
            )

      # Stage 0b: Parse Pasted Grocery List if raw text provided
      if pasted_list_text and pasted_list_text.strip():
        with tracer.start_span(
            "tool.parse_pasted_grocery_list",
            raw_char_length=len(pasted_list_text),
        ) as parse_span:
          parsed_from_text = parse_pasted_grocery_list(pasted_list_text)
          parse_span.set_attribute("parsed.item_count", len(parsed_from_text))
          items = parsed_from_text

      if not items:
        raise ValueError("Shopping list must contain at least one item.")
      root_span.set_attribute("item_count", len(items))

      # Stage 1: Context & Memory Hydration
      with tracer.start_span("memory.hydrate_user_context") as mem_span:
        profile = self.memory.get_user_profile(user_id=user_id)
        location = override_location or profile["home_coordinate"]
        active_programs = (
            override_loyalty_programs
            if override_loyalty_programs is not None
            else profile["active_loyalty_programs"]
        )
        fuel_cost_per_km = profile["fuel_cost_per_km"]
        historical_prices = {}
        for cat in CANONICAL_CATALOG:
          sku_id = cat["sku_id"]
          hp = self.memory.get_historical_sku_price(sku_id)
          if hp is not None:
            historical_prices[sku_id] = hp

        if not shopping_list_title or not shopping_list_title.strip():
          date_str = datetime.datetime.now(datetime.timezone.utc).strftime(
              "%Y-%m-%d"
          )
          shopping_list_title = f"Weekly Grocery List ({date_str})"

        mem_span.set_attribute("user.home_label", location.label)
        mem_span.set_attribute(
            "user.active_loyalty_count", len(active_programs)
        )
        mem_span.set_attribute(
            "memory.historical_skus_loaded", len(historical_prices)
        )

      # Stage 2: Geospatial Store Discovery within 20km Radius + Online UK Shops
      with tracer.start_span(
          "tool.discover_stores_within_radius",
          latitude=location.latitude,
          longitude=location.longitude,
          radius_km=radius_km,
          include_online_shops=include_online_shops,
      ) as geo_span:
        stores_within, stores_excluded = discover_stores_within_radius(
            user_location=location,
            radius_km=radius_km,
            include_online_shops=include_online_shops,
        )
        physical_in_radius = [
            s for s in stores_within if s.store_type != "ONLINE_UK"
        ]
        online_included = [
            s for s in stores_within if s.store_type == "ONLINE_UK"
        ]
        tracer.metrics.set_gauge(
            "grocery.stores_in_20km_radius", float(len(physical_in_radius))
        )
        tracer.metrics.set_gauge(
            "grocery.online_stores_evaluated", float(len(online_included))
        )
        tracer.metrics.set_gauge(
            "grocery.stores_excluded_beyond_20km", float(len(stores_excluded))
        )
        geo_span.set_attribute("stores.within_radius", len(physical_in_radius))
        geo_span.set_attribute("stores.online_uk", len(online_included))
        geo_span.set_attribute("stores.excluded", len(stores_excluded))
        for ex in stores_excluded:
          geo_span.add_event(
              "store_excluded_outside_radius",
              store_id=ex.store_id,
              store_name=ex.name,
              distance_km=ex.distance_km,
              max_radius_km=radius_km,
          )

      if not stores_within:
        raise RuntimeError(
            f"No grocery stores found within {radius_km} km of ({location.latitude}, {location.longitude})."
        )

      # Stage 3: Multi-Store Catalog Quotes & Online Validity Audit (GBP £)
      store_quotes: list[StoreBasketQuote] = []
      online_validity_audit: list[dict[str, Any]] = []
      with tracer.start_span(
          "orchestrator.evaluate_all_stores_in_radius",
          store_count=len(stores_within),
      ):
        for store in stores_within:
          with tracer.start_span(
              "tool.fetch_store_catalog_quote",
              store_id=store.store_id,
              store_name=store.name,
              distance_km=store.distance_km,
          ) as quote_span:
            quote = fetch_store_catalog_quote(
                store=store,
                items=items,
                user_active_programs=active_programs,
                fuel_cost_per_km=fuel_cost_per_km,
                historical_price_lookup=historical_prices,
            )
            store_quotes.append(quote)
            quote_span.set_attribute(
                "quote.can_fulfill_entire_list", quote.can_fulfill_entire_list
            )
            quote_span.set_attribute(
                "quote.fulfillment_coverage_pct", quote.fulfillment_coverage_pct
            )
            quote_span.set_attribute(
                "quote.regular_subtotal_gbp", quote.regular_subtotal
            )
            quote_span.set_attribute(
                "quote.loyalty_subtotal_gbp", quote.loyalty_subtotal
            )
            quote_span.set_attribute(
                "quote.effective_best_total_gbp", quote.effective_best_total
            )
            quote_span.set_attribute(
                "loyalty.is_advantageous",
                quote.loyalty_analysis.is_advantageous,
            )
            quote_span.set_attribute(
                "loyalty.net_weekly_advantage_gbp",
                quote.loyalty_analysis.net_weekly_advantage,
            )
            tracer.metrics.observe_histogram(
                "grocery.store_effective_total_gbp", quote.effective_best_total
            )
            if store.store_type == "ONLINE_UK":
              online_validity_audit.append({
                  "store_id": store.store_id,
                  "store_name": store.name,
                  "chain": store.chain,
                  "can_fulfill_entire_list": quote.can_fulfill_entire_list,
                  "fulfilled_item_count": quote.fulfilled_item_count,
                  "total_requested_item_count": quote.total_requested_item_count,
                  "fulfillment_coverage_pct": quote.fulfillment_coverage_pct,
                  "supported_items": [li.requested_item for li in quote.line_items],
                  "missing_items": quote.missing_items,
                  "eligible_subtotal_gbp": quote.effective_best_total,
                  "online_validity_note": quote.online_validity_note,
              })

      # Rank full-basket 20km supermarkets first so best_single can fulfill 100% of the list
      store_quotes.sort(
          key=lambda q: (not q.can_fulfill_entire_list, q.effective_best_total)
      )
      full_basket_quotes = [
          q for q in store_quotes if q.can_fulfill_entire_list
      ]
      best_single = (
          full_basket_quotes[0] if full_basket_quotes else store_quotes[0]
      )
      worst_single = (
          full_basket_quotes[-1] if full_basket_quotes else store_quotes[-1]
      )
      max_savings_vs_worst = round(
          worst_single.total_regular_with_travel
          - best_single.effective_best_total,
          2,
      )
      tracer.metrics.set_gauge(
          "grocery.max_weekly_savings_gbp", max_savings_vs_worst
      )

      # Stage 4: Online + Regular 20km Shop Hybrid Plan & 2-Store Split Optimization
      with tracer.start_span("tool.optimize_split_basket_strategy") as split_span:
        online_hybrid_plan = build_online_plus_regular_shop_plan(
            store_quotes=store_quotes,
            fuel_cost_per_km=fuel_cost_per_km,
        )
        split_option = optimize_split_basket_strategy(
            store_quotes=store_quotes,
            user_location=location,
            fuel_cost_per_km=fuel_cost_per_km,
        )
        # Ensure if an online_hybrid_plan exists, we expose it both in online_hybrid_plan and best_split_basket
        if online_hybrid_plan and (
            split_option is None
            or online_hybrid_plan.total_cost_with_travel <= split_option.total_cost_with_travel
        ):
          split_option = online_hybrid_plan

        if split_option:
          split_span.set_attribute(
              "split.total_cost_with_travel_gbp",
              split_option.total_cost_with_travel,
          )
          split_span.set_attribute(
              "split.savings_vs_single_gbp",
              split_option.savings_vs_best_single_store,
          )
          split_span.set_attribute(
              "split.recommended", split_option.is_recommended_over_single
          )

      if split_option and split_option.is_recommended_over_single:
        winning_strategy_type = "SPLIT_BASKET"
        winning_total_cost = split_option.total_cost_with_travel
        store_names = " + ".join(s.store_name for s in split_option.stores)
        winning_store_summary = f"Hybrid Online + Regular Shop: {store_names}"
      else:
        winning_strategy_type = "SINGLE_STORE"
        winning_total_cost = best_single.effective_best_total
        winning_store_summary = (
            f"{best_single.store.name} ({best_single.store.distance_km} km)"
        )

      partial_online_count = sum(
          1 for a in online_validity_audit if not a["can_fulfill_entire_list"]
      )
      validity_headline = (
          f"Online Shop Validity Check: {partial_online_count}/{len(online_validity_audit)} online shops "
          f"(Amazon UK, Grape Tree, Whole Food Earth) CANNOT fulfill your whole list standalone because they only "
          f"stock ambient wholefoods/pantry and cannot ship fresh/chilled meat, dairy, eggs, or produce. "
          if partial_online_count > 0
          else "Online Shop Validity Check: All items on this list are ambient wholefoods/pantry and can be fulfilled online. "
      )

      draft_summary = (
          f"Evaluated {len(physical_in_radius)} supermarkets within {radius_km:.0f}km of {location.label} "
          f"plus {len(online_included)} UK online retailers. "
          f"{validity_headline}"
          f"Best single regular 20km supermarket for 100% of your list is {best_single.store.name} "
          f"at £{best_single.effective_best_total:.2f} (saving £{max_savings_vs_worst:.2f} vs highest-cost regular store). "
          f"{online_hybrid_plan.rationale if online_hybrid_plan else (split_option.rationale if split_option else '')}"
      )

      # Stage 5: Context Bloat Compaction & Model-Routed LLM Synthesis
      history_runs = self.memory.list_shopping_history(user_id=user_id, limit=10)
      compacted_context = self.context_manager.build_compacted_prompt_context(
          agent_role="COORDINATOR_AGENT",
          user_profile=profile,
          history_runs=history_runs,
          quotes=store_quotes,
      )
      routing_decisions.append(
          self.model_router.route_task(
              task_name="evaluate_loyalty_roi_and_online_split_tradeoffs",
              agent_name="PricingAndLoyaltySubAgent",
              complexity_tier="HIGH",
              estimated_prompt_tokens=compacted_context["compacted_context_tokens"],
              requires_multi_store_tradeoff=True,
          )
      )
      executive_summary = self.model_router.generate_executive_advice(
          compacted_context=compacted_context,
          deterministic_draft_summary=draft_summary,
          tracer=tracer,
      )

      # Stage 6: Output Guardrails (Anti-Hallucination & 100% Single-Store Fulfillment)
      verified_store_ids = {s.store_id for s in stores_within}
      output_guardrail_verdict = self.guardrails.validate_output_guardrails(
          best_single=best_single,
          online_hybrid_plan=online_hybrid_plan,
          verified_store_ids=verified_store_ids,
          executive_summary=executive_summary,
          tracer=tracer,
      )

      # Stage 7: Human-in-the-Loop (HITL) Approval Checkpoint
      hitl_req = self.hitl_gate.evaluate_hitl_checkpoint(
          winning_total_cost_gbp=winning_total_cost,
          best_single=best_single,
          winning_strategy_type=winning_strategy_type,
          spend_threshold_gbp=hitl_spend_threshold_gbp,
          tracer=tracer,
      )

      root_span.set_attribute("result.winning_strategy", winning_strategy_type)
      root_span.set_attribute("result.winning_total_cost_gbp", winning_total_cost)
      root_span.set_attribute("hitl.status", hitl_req.status)

    trace_summary = tracer.export_trace_summary()

    excluded_dicts = [
        {
            "store_id": s.store_id,
            "name": s.name,
            "distance_km": s.distance_km,
            "reason": f"Distance {s.distance_km}km exceeds {radius_km}km radius limit from {location.label}",
        }
        for s in stores_excluded
    ]

    agent_metadata = {
        "coordinator_agent": self.adk_hierarchy["root_agent"].name,
        "sub_agents": [a.name for a in self.adk_hierarchy["sub_agents"]],
        "model_routing_decisions": routing_decisions,
        "input_guardrails": input_guardrail_verdict,
        "output_guardrails": output_guardrail_verdict,
        "context_window_compaction": {
            "raw_unpruned_tokens": compacted_context["raw_unpruned_tokens"],
            "compacted_context_tokens": compacted_context["compacted_context_tokens"],
            "tokens_saved_by_compaction": compacted_context["tokens_saved_by_compaction"],
            "within_token_budget": compacted_context["within_token_budget"],
        },
        "async_memory_worker_enabled": True,
    }

    recommendation = OptimizationRecommendation(
        run_id=run_id,
        shopping_list_id=list_id,
        shopping_list_title=shopping_list_title,
        created_at_iso=now_iso,
        user_location=location,
        search_radius_km=radius_km,
        stores_evaluated_count=len(stores_within) + len(stores_excluded),
        stores_within_radius_count=len(stores_within),
        stores_excluded_outside_radius=excluded_dicts,
        ranked_single_stores=store_quotes,
        best_single_store=best_single,
        best_split_basket=split_option,
        winning_strategy_type=winning_strategy_type,
        winning_total_cost=winning_total_cost,
        max_savings_vs_worst_store=max_savings_vs_worst,
        executive_summary=executive_summary,
        trace_id=tracer.trace_id,
        trace_summary=trace_summary,
        online_hybrid_plan=online_hybrid_plan,
        online_validity_audit=online_validity_audit,
        agent_metadata=agent_metadata,
        hitl_checkpoint=hitl_req.to_dict(),
    )

    if persist_run:
      self.async_memory.enqueue_background_run_persistence(
          user_id=user_id,
          title=shopping_list_title,
          items=items,
          winning_strategy_type=winning_strategy_type,
          winning_store_summary=winning_store_summary,
          winning_total_cost=winning_total_cost,
          loyalty_savings_usd=best_single.loyalty_analysis.total_weekly_member_benefit,
          recommendation_dict=recommendation.to_dict(),
          list_id=list_id,
          wait_for_completion=True,
      )

    return recommendation
