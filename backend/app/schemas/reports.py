"""Typed API responses for Cash & Credit Intelligence reports."""

from datetime import date

from pydantic import BaseModel, Field


class AgingBucketsResponse(BaseModel):
    not_yet_due: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    days_90_plus: float
    total_open: float
    total_overdue: float
    reasons: list[str]


class MethodologyFormulasResponse(BaseModel):
    due_date: str
    settlement_date: str
    behaviour_owed: str
    open_remaining: str
    risk_score: str
    risk_bands: str
    trend: str
    suggested_credit_limit: str
    expected_in: str
    expected_out: str
    conservative_series: str


class MethodologyThresholdsResponse(BaseModel):
    aging_1_30_max_days: int
    aging_31_60_max_days: int
    aging_61_90_max_days: int
    risk_history_window_days: int
    risk_min_settled_invoices: int
    lateness_max_points: float
    lateness_cap_days: int
    late_frequency_max_points: float
    overdue_now_max_points: float
    oldest_overdue_cap_days: int
    utilisation_max_points: float
    utilisation_start_ratio: float
    utilisation_full_ratio: float
    reliable_score_upper_bound: float
    watch_score_upper_bound: float
    risk_score_min: float
    risk_score_max: float
    trend_window_days: int
    trend_min_settled_invoices_per_window: int
    reliable_peak_outstanding_multiplier: float
    risky_current_limit_multiplier: float
    credit_limit_rounding_increment: float
    next_5_weeks_count: int
    next_5_weeks_days_per_week: int
    next_5_weeks_horizon_days: int
    projection_median_days_late_cap: int


class MethodologyResponse(BaseModel):
    defaults_note: str
    data_quality_note: str
    median_lateness_rule: str
    formulas: MethodologyFormulasResponse
    thresholds: MethodologyThresholdsResponse


class ReceivablesCustomerResponse(BaseModel):
    customer_id: int
    customer_name: str
    credit_balance: float = Field(
        description="Credit the business owes this customer; never netted against overdue receivables."
    )
    outstanding: float
    overdue: float
    aging: AgingBucketsResponse
    reasons: list[str]


class ReceivablesTotalsResponse(BaseModel):
    total_outstanding: float
    total_overdue: float
    total_customer_credit_balance: float
    aging: AgingBucketsResponse
    reasons: list[str]


class ReceivablesReportResponse(BaseModel):
    as_of_date: date
    totals: ReceivablesTotalsResponse
    customers: list[ReceivablesCustomerResponse]
    methodology: MethodologyResponse


class RiskComponentsResponse(BaseModel):
    settled_invoice_count: int
    late_invoice_count: int
    average_days_late: float | None
    late_payment_share: float | None
    oldest_overdue_days: int
    current_outstanding: float
    credit_limit: float
    utilisation_ratio: float | None
    lateness_points: float | None
    frequency_points: float | None
    overdue_now_points: float | None
    utilisation_points: float | None


class SuggestedCreditLimitResponse(BaseModel):
    suggested_limit: float | None
    current_limit: float
    current_outstanding: float
    peak_outstanding_last_180_days: float
    multiplier: float | None
    rounding_increment: float | None
    reasons: list[str]


class CustomerRiskResponse(BaseModel):
    customer_id: int
    customer_name: str
    credit_balance: float = Field(
        description="Credit the business owes this customer; never netted against overdue receivables."
    )
    score: float | None
    band: str
    trend: str | None
    trend_recent_invoice_count: int
    trend_previous_invoice_count: int
    trend_recent_average_days_late: float | None
    trend_previous_average_days_late: float | None
    open_outstanding: float
    open_overdue: float
    aging: AgingBucketsResponse
    components: RiskComponentsResponse
    suggested_credit_limit: SuggestedCreditLimitResponse
    reasons: list[str]


class CustomerRiskReportResponse(BaseModel):
    as_of_date: date
    customers: list[CustomerRiskResponse]
    methodology: MethodologyResponse


class ProjectedInvoiceReceiptResponse(BaseModel):
    invoice_id: int
    customer_id: int
    customer_name: str
    remaining_amount: float
    due_date: date
    median_days_late: float = Field(
        description="Raw median historical days late before the whole-day scheduling round-up."
    )
    scheduled_days_late: int = Field(
        description="Median lateness rounded up to a whole day for expected receipt scheduling."
    )
    expected_date: date
    customer_band: str
    included_in_conservative_series: bool
    week_number: int | None
    reasons: list[str]


class ProjectedPurchaseOutflowResponse(BaseModel):
    purchase_id: int
    supplier_id: int
    supplier_name: str
    remaining_amount: float
    due_date: date
    expected_date: date
    week_number: int | None
    reasons: list[str]


class CashProjectionWeekResponse(BaseModel):
    week_number: int
    start_date: date
    end_date: date
    expected_in: float
    expected_out: float
    net_movement: float
    cumulative_net: float
    conservative_expected_in: float
    conservative_net_movement: float
    conservative_cumulative_net: float
    projected_balance: float | None
    conservative_projected_balance: float | None
    reasons: list[str]


class NextFiveWeeksCashFlowResponse(BaseModel):
    opening_balance: float | None = Field(
        default=None,
        description="Optional caller-provided balance for display only; it is never stored or inferred."
    )
    weeks: list[CashProjectionWeekResponse] = Field(
        description="Five full seven-day buckets beginning on as_of_date."
    )
    projected_invoice_receipts: list[ProjectedInvoiceReceiptResponse]
    projected_purchase_outflows: list[ProjectedPurchaseOutflowResponse]
    reasons: list[str]


class CashFlowReportResponse(BaseModel):
    as_of_date: date
    next_5_weeks: NextFiveWeeksCashFlowResponse = Field(
        description="Cash movement projection for the next 5 weeks (five full weekly buckets)."
    )
    methodology: MethodologyResponse
