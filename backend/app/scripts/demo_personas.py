"""The planted customers used by the deterministic demo-data generator.

This is deliberately the one source of truth for the scenarios.  Tests import
these definitions rather than maintaining a second set of expected analytics
outcomes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoPersona:
    key: str
    customer_name: str
    credit_limit: float
    payment_terms_days: int
    expected_band: str
    expected_trend: str | None
    settlement_offsets: tuple[int, ...]
    settled_payment_lateness_days: tuple[int, ...]
    settled_invoice_amount: float
    open_invoice_overdue_days: int | None = None
    open_invoice_amount: float | None = None
    creates_credit_balance: bool = False


PERSONAS: tuple[DemoPersona, ...] = (
    DemoPersona(
        key="RELIABLE",
        customer_name="Reliable Retailers",
        credit_limit=30_000,
        payment_terms_days=14,
        expected_band="RELIABLE",
        expected_trend="STABLE",
        settlement_offsets=(-170, -140, -110, -80, -50, -20),
        settled_payment_lateness_days=(0, 1, 2, 0, 1, 2),
        settled_invoice_amount=1_000,
    ),
    DemoPersona(
        key="CHRONICALLY_LATE",
        customer_name="Chronic Late Stores",
        credit_limit=20_000,
        payment_terms_days=10,
        expected_band="RISKY",
        expected_trend="STABLE",
        settlement_offsets=(-170, -155, -140, -125, -110, -95, -85, -70, -55, -40, -25, -10),
        settled_payment_lateness_days=(30, 30, 30, 30, 30, 0, 30, 30, 30, 30, 30, 0),
        settled_invoice_amount=1_000,
        open_invoice_overdue_days=40,
        open_invoice_amount=3_000,
    ),
    DemoPersona(
        key="WORSENING",
        customer_name="Worsening Wholesale",
        credit_limit=30_000,
        payment_terms_days=7,
        expected_band="WATCH",
        expected_trend="WORSENING",
        settlement_offsets=(-170, -145, -100, -60, -40, -20),
        settled_payment_lateness_days=(0, 0, 0, 30, 30, 30),
        settled_invoice_amount=1_000,
        open_invoice_overdue_days=20,
        open_invoice_amount=1_200,
    ),
    DemoPersona(
        key="NEAR_LIMIT",
        customer_name="Near Limit Mart",
        credit_limit=10_000,
        payment_terms_days=7,
        expected_band="WATCH",
        expected_trend="STABLE",
        settlement_offsets=(-170, -140, -110, -80, -50, -20),
        settled_payment_lateness_days=(0, 1, 2, 0, 1, 2),
        settled_invoice_amount=1_000,
        open_invoice_overdue_days=35,
        open_invoice_amount=9_500,
    ),
    DemoPersona(
        key="NEW",
        customer_name="Newly Opened Shop",
        credit_limit=12_000,
        payment_terms_days=14,
        expected_band="INSUFFICIENT_HISTORY",
        expected_trend=None,
        settlement_offsets=(-75, -25),
        settled_payment_lateness_days=(0, 1),
        settled_invoice_amount=1_000,
    ),
    DemoPersona(
        key="CREDIT_HOLDER",
        customer_name="Credit Holder Traders",
        credit_limit=25_000,
        payment_terms_days=14,
        expected_band="RELIABLE",
        expected_trend="STABLE",
        settlement_offsets=(-170, -140, -110, -80, -50, -20),
        settled_payment_lateness_days=(0, 1, 2, 0, 1, 2),
        settled_invoice_amount=1_000,
        creates_credit_balance=True,
    ),
)


PERSONAS_BY_KEY = {persona.key: persona for persona in PERSONAS}
