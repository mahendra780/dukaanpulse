"""Plain input and output rows used by the analytics calculation core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CustomerInput:
    """The customer fields needed for receivables, risk, and projections."""

    customer_id: int
    customer_name: str
    credit_limit: float
    credit_balance: float
    payment_terms_days: int


@dataclass(frozen=True)
class InvoiceInput:
    """A non-line-item invoice row; invoice totals are sufficient here."""

    invoice_id: int
    customer_id: int
    invoice_date: date
    total_amount: float
    status: str


@dataclass(frozen=True)
class PaymentInput:
    """A customer payment, including system-created credit rows."""

    payment_id: int
    invoice_id: int
    payment_date: date
    amount: float
    payment_method: str


@dataclass(frozen=True)
class SupplierInput:
    """The supplier fields needed for projected purchase outflows."""

    supplier_id: int
    supplier_name: str
    payment_terms_days: int


@dataclass(frozen=True)
class PurchaseInput:
    """A supplier purchase row used by the cash-projection calculation."""

    purchase_id: int
    supplier_id: int
    purchase_date: date
    total_amount: float
    status: str


@dataclass(frozen=True)
class SupplierPaymentInput:
    """A payment against a supplier purchase."""

    purchase_payment_id: int
    purchase_id: int
    payment_date: date
    amount: float


@dataclass(frozen=True)
class InvoiceAnalysis:
    """Explainable payment, settlement, and open-balance state for one invoice."""

    invoice_id: int
    customer_id: int
    invoice_date: date
    due_date: date
    total_amount: float
    credit_payment_amount: float
    real_payment_amount: float
    total_payment_amount: float
    behaviour_owed_amount: float
    remaining_amount: float
    settlement_date: date | None
    days_late: int | None
    overdue_days: int
    is_open: bool
    excluded_from_lateness: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AgingBuckets:
    """Open receivables split by the D24 days-past-due buckets."""

    not_yet_due: float
    days_1_30: float
    days_31_60: float
    days_61_90: float
    days_90_plus: float
    total_open: float
    total_overdue: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RiskComponents:
    """Every input and point contribution used by the D25 risk formula."""

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


@dataclass(frozen=True)
class CreditLimitSuggestion:
    """A transparent, non-binding D26 credit-limit suggestion."""

    suggested_limit: float | None
    current_limit: float
    current_outstanding: float
    peak_outstanding_last_180_days: float
    multiplier: float | None
    rounding_increment: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CustomerRisk:
    """A customer's explainable risk result and non-binding limit suggestion."""

    customer_id: int
    customer_name: str
    score: float | None
    band: str
    trend: str | None
    trend_recent_invoice_count: int
    trend_previous_invoice_count: int
    trend_recent_average_days_late: float | None
    trend_previous_average_days_late: float | None
    components: RiskComponents
    aging: AgingBuckets
    suggested_credit_limit: CreditLimitSuggestion
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ReceivablesTotals:
    """Portfolio receivables, aging, and customer credit kept separate."""

    total_outstanding: float
    total_overdue: float
    total_customer_credit_balance: float
    aging: AgingBuckets
    invoice_analyses: tuple[InvoiceAnalysis, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProjectedInvoiceReceipt:
    """One open-invoice input to the expected-IN side of the projection."""

    invoice_id: int
    customer_id: int
    customer_name: str
    remaining_amount: float
    due_date: date
    median_days_late: float
    scheduled_days_late: int
    expected_date: date
    customer_band: str
    included_in_conservative_series: bool
    week_number: int | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProjectedPurchaseOutflow:
    """One unpaid purchase input to the expected-OUT side of the projection."""

    purchase_id: int
    supplier_id: int
    supplier_name: str
    remaining_amount: float
    due_date: date
    expected_date: date
    week_number: int | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CashProjectionWeek:
    """One seven-day bucket of standard and conservative cash movement."""

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
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CashProjection:
    """Five-week net-movement forecast; no cash-on-hand is persisted or inferred."""

    today: date
    opening_balance: float | None
    weeks: tuple[CashProjectionWeek, ...]
    projected_invoice_receipts: tuple[ProjectedInvoiceReceipt, ...]
    projected_purchase_outflows: tuple[ProjectedPurchaseOutflow, ...]
    reasons: tuple[str, ...]
