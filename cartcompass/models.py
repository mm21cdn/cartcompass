"""Domain models and strict tool schemas for the Grocery Price Optimization App."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class UnitType(str, Enum):
  COUNT = "count"
  KG = "kg"
  GRAM = "g"
  LITER = "l"
  ML = "ml"
  LOAF = "loaf"
  DOZEN = "dozen"
  PACK = "pack"


class LoyaltyRecommendationTier(str, Enum):
  ALREADY_MEMBER_ACTIVE = "ALREADY_MEMBER_ACTIVE"
  HIGHLY_ADVANTAGEOUS_FREE = "HIGHLY_ADVANTAGEOUS_FREE"
  HIGHLY_ADVANTAGEOUS_PAID = "HIGHLY_ADVANTAGEOUS_PAID"
  MARGINAL_PAYBACK = "MARGINAL_PAYBACK"
  NOT_ADVANTAGEOUS = "NOT_ADVANTAGEOUS"


@dataclass(frozen=True)
class GeoCoordinate:
  latitude: float
  longitude: float
  label: str = "Home"
  postcode: str = "PO20 3SJ"

  def validate(self) -> None:
    if not (-90.0 <= self.latitude <= 90.0):
      raise ValueError(f"Invalid latitude: {self.latitude}")
    if not (-180.0 <= self.longitude <= 180.0):
      raise ValueError(f"Invalid longitude: {self.longitude}")


@dataclass
class ShoppingItemInput:
  name: str
  quantity: float = 1.0
  unit: str = "count"
  preferred_brand: str | None = None
  allow_substitutions: bool = True
  category: str = "general"

  def __post_init__(self) -> None:
    self.name = self.name.strip()
    if not self.name:
      raise ValueError("Shopping item name cannot be empty.")
    if self.quantity <= 0:
      raise ValueError(f"Quantity must be positive for {self.name}")


@dataclass
class LoyaltyProgramSpec:
  program_id: str
  program_name: str
  annual_fee: float
  signup_bonus_credit: float
  points_cashback_rate: float  # e.g. 0.02 for 2% cashback in points
  perks_summary: str


@dataclass
class GroceryStore:
  store_id: str
  name: str
  chain: str
  coordinate: GeoCoordinate
  address: str
  loyalty_program: LoyaltyProgramSpec
  distance_km: float = 0.0
  within_radius: bool = True
  estimated_drive_minutes: float = 0.0
  store_type: str = "PHYSICAL_20KM"  # "PHYSICAL_20KM" or "ONLINE_UK"
  standard_delivery_fee: float = 0.0
  free_delivery_threshold: float = 0.0
  catalog_scope: str = "FULL_SUPERMARKET"  # "FULL_SUPERMARKET", "ONLINE_WHOLEFOOD_SPECIALIST", "ONLINE_AMBIENT_PANTRY"


@dataclass
class MatchedLineItem:
  requested_item: str
  matched_sku_id: str
  matched_product_name: str
  quantity: float
  unit: str
  regular_unit_price: float
  loyalty_unit_price: float
  regular_line_total: float
  loyalty_line_total: float
  loyalty_savings: float
  is_substituted: bool = False
  promo_badge: str | None = None
  historical_avg_price: float | None = None
  price_vs_history_pct: float | None = None
  item_category: str = "FRESH_CHILLED"  # "FRESH_CHILLED" or "AMBIENT_WHOLEFOOD"


@dataclass
class LoyaltyAdvantageAnalysis:
  store_id: str
  store_name: str
  program_name: str
  user_already_member: bool
  annual_membership_fee: float
  amortized_weekly_fee: float
  gross_weekly_loyalty_discount: float
  points_cashback_value: float
  total_weekly_member_benefit: float
  net_weekly_advantage: float
  projected_annual_net_savings: float
  breakeven_weeks: float | None
  is_advantageous: bool
  recommendation_tier: LoyaltyRecommendationTier
  rationale: str


@dataclass
class StoreBasketQuote:
  store: GroceryStore
  line_items: list[MatchedLineItem]
  missing_items: list[str]
  regular_subtotal: float
  loyalty_subtotal: float
  estimated_roundtrip_fuel_cost: float
  total_regular_with_travel: float
  total_loyalty_with_travel: float
  effective_best_total: float
  effective_uses_loyalty: bool
  loyalty_analysis: LoyaltyAdvantageAnalysis
  can_fulfill_entire_list: bool = True
  fulfilled_item_count: int = 0
  total_requested_item_count: int = 0
  fulfillment_coverage_pct: float = 100.0
  online_validity_note: str = ""


@dataclass
class SplitStoreAllocation:
  store_id: str
  store_name: str
  distance_km: float
  use_loyalty: bool
  assigned_items: list[MatchedLineItem]
  subtotal: float
  store_type: str = "PHYSICAL_20KM"
  delivery_or_fuel_fee: float = 0.0


@dataclass
class SplitBasketOption:
  stores: list[SplitStoreAllocation]
  combined_item_subtotal: float
  multi_stop_route_km: float
  multi_stop_fuel_cost: float
  total_cost_with_travel: float
  savings_vs_best_single_store: float
  is_recommended_over_single: bool
  rationale: str
  plan_type: str = "TWO_STORE_SPLIT"  # "ONLINE_PLUS_REGULAR_SHOP" or "TWO_STORE_SPLIT"
  online_validity_summary: str = ""
  free_delivery_tip: str = ""


@dataclass
class ToolExecutionEnvelope:
  """Standardized LLM-guided tool output & actionable error recovery envelope."""

  status: str  # "success" or "error"
  tool_name: str
  data: Any = None
  error_code: str | None = None
  error_message: str | None = None
  llm_recovery_instructions: str | None = None
  retriable: bool = True
  suggested_arguments: dict[str, Any] = field(default_factory=dict)
  output_schema_version: str = "1.0"

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)


@dataclass
class HITLApprovalRequest:
  """Human-in-the-Loop (HITL) approval gate checkpoint for high-spend or paid-membership actions."""

  request_id: str
  status: str  # "AUTO_APPROVED_BELOW_THRESHOLD", "PENDING_HUMAN_APPROVAL", "APPROVED", "REJECTED"
  requires_human_confirmation: bool
  trigger_reason: str
  basket_total_gbp: float
  spend_threshold_gbp: float
  recommended_action_summary: str
  created_at_iso: str

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)


@dataclass
class OptimizationRecommendation:
  run_id: str
  shopping_list_id: str
  shopping_list_title: str
  created_at_iso: str
  user_location: GeoCoordinate
  search_radius_km: float
  stores_evaluated_count: int
  stores_within_radius_count: int
  stores_excluded_outside_radius: list[dict[str, Any]]
  ranked_single_stores: list[StoreBasketQuote]
  best_single_store: StoreBasketQuote
  best_split_basket: SplitBasketOption | None
  winning_strategy_type: str  # "SINGLE_STORE" or "SPLIT_BASKET"
  winning_total_cost: float
  max_savings_vs_worst_store: float
  executive_summary: str
  trace_id: str
  trace_summary: dict[str, Any]
  online_hybrid_plan: SplitBasketOption | None = None
  online_validity_audit: list[dict[str, Any]] = field(default_factory=list)
  agent_metadata: dict[str, Any] = field(default_factory=dict)
  hitl_checkpoint: dict[str, Any] = field(default_factory=dict)

  def to_dict(self) -> dict[str, Any]:
    return asdict(self)
