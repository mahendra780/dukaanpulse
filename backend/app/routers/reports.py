"""Authenticated Cash & Credit Intelligence report endpoints."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import require_permission
from app.db.database import get_db
from app.schemas.reports import (
    CashFlowReportResponse,
    CustomerRiskReportResponse,
    MethodologyFormulasResponse,
    MethodologyResponse,
    MethodologyThresholdsResponse,
    ReceivablesReportResponse,
)
from app.services.analytics import config
from app.services.analytics.calculations import (
    calculate_cash_projection,
    calculate_customer_risk,
    calculate_receivables_totals,
)
from app.services.analytics.loaders import AnalyticsInputs, load_report_inputs


router = APIRouter(prefix="/reports", tags=["Reports"])


def get_reports_now() -> datetime:
    """Supply the current UTC instant; tests can override this dependency."""
    return datetime.now(timezone.utc)


def get_reports_today(now: datetime = Depends(get_reports_now)) -> date:
    """Return the report snapshot date in the configured business timezone."""
    return now.astimezone(ZoneInfo(settings.BUSINESS_TIMEZONE)).date()


def _methodology() -> MethodologyResponse:
    """Expose the configuration-derived rules so clients never duplicate them."""
    return MethodologyResponse(
        defaults_note=(
            "These thresholds are defaults calibrated on synthetic demo data; "
            "they are transparent rules, not machine-learning predictions."
        ),
        data_quality_note=(
            "Record payment_date as the date money actually arrived. "
            "Incorrect payment dates change settlement, lateness, risk, and expected cash timing."
        ),
        median_lateness_rule=(
            "Expected invoice receipts use the customer's median days late from eligible settled invoices. "
            f"It is 0 when history is insufficient, capped at {config.PROJECTION_MEDIAN_DAYS_LATE_CAP} days, "
            "then any fractional median is rounded UP to the next whole day for scheduling. "
            "Both median_days_late (raw) and scheduled_days_late (whole-day value) are returned."
        ),
        formulas=MethodologyFormulasResponse(
            due_date="invoice_date + customer.payment_terms_days",
            settlement_date=(
                "The payment_date on which cumulative REAL payments (CASH, UPI, BANK_TRANSFER, CHEQUE) "
                "first reach amount owed."
            ),
            behaviour_owed=(
                "invoice total - RETURN_CREDIT and CREDIT_APPLIED rows; if this is 0, the invoice is excluded "
                "from payment-behaviour lateness."
            ),
            open_remaining="invoice total - all payment rows, including credit rows; customer credit balance is never netted.",
            risk_score=(
                f"lateness = {config.LATENESS_MAX_POINTS:g} x min(avg days late, "
                f"{config.LATENESS_CAP_DAYS}) / {config.LATENESS_CAP_DAYS}; frequency = "
                f"{config.LATE_FREQUENCY_MAX_POINTS:g} x late-invoice share; overdue-now = "
                f"{config.OVERDUE_NOW_MAX_POINTS:g} x min(oldest overdue days, "
                f"{config.OLDEST_OVERDUE_CAP_DAYS}) / {config.OLDEST_OVERDUE_CAP_DAYS}; utilisation = "
                f"{config.UTILISATION_MAX_POINTS:g} x clamp((outstanding / credit limit - "
                f"{config.UTILISATION_START_RATIO:g}) / "
                f"{config.UTILISATION_FULL_RATIO - config.UTILISATION_START_RATIO:g}, 0, 1)."
            ),
            risk_bands=(
                f"RELIABLE below {config.RELIABLE_SCORE_UPPER_BOUND:g}; WATCH from "
                f"{config.RELIABLE_SCORE_UPPER_BOUND:g} to {config.WATCH_SCORE_UPPER_BOUND - 1:g}; "
                f"RISKY at or above {config.WATCH_SCORE_UPPER_BOUND:g}."
            ),
            trend=(
                f"Average days late in the last {config.TREND_WINDOW_DAYS} days compared with the preceding "
                f"{config.TREND_WINDOW_DAYS} days; each window needs at least "
                f"{config.TREND_MIN_SETTLED_INVOICES_PER_WINDOW} settled invoices."
            ),
            suggested_credit_limit=(
                f"Suggestion only: RELIABLE uses max(current limit, "
                f"{config.RELIABLE_PEAK_OUTSTANDING_MULTIPLIER:g} x peak outstanding) rounded up to "
                f"{config.CREDIT_LIMIT_ROUNDING_INCREMENT:,.0f}; WATCH keeps current limit; RISKY uses "
                f"max(current outstanding, {config.RISKY_CURRENT_LIMIT_MULTIPLIER:g} x current limit) rounded "
                f"to {config.CREDIT_LIMIT_ROUNDING_INCREMENT:,.0f} and never below current outstanding."
            ),
            expected_in=(
                "For each open invoice: remaining amount on max(due date, as-of date) plus median days late."
            ),
            expected_out=(
                "For each non-cancelled purchase with a remaining balance: purchase date + supplier payment terms, "
                "or the as-of date when already past due."
            ),
            conservative_series="Expected IN excludes customers banded RISKY; expected OUT is unchanged.",
        ),
        thresholds=MethodologyThresholdsResponse(
            aging_1_30_max_days=config.AGING_1_30_MAX_DAYS,
            aging_31_60_max_days=config.AGING_31_60_MAX_DAYS,
            aging_61_90_max_days=config.AGING_61_90_MAX_DAYS,
            risk_history_window_days=config.RISK_HISTORY_WINDOW_DAYS,
            risk_min_settled_invoices=config.RISK_MIN_SETTLED_INVOICES,
            lateness_max_points=config.LATENESS_MAX_POINTS,
            lateness_cap_days=config.LATENESS_CAP_DAYS,
            late_frequency_max_points=config.LATE_FREQUENCY_MAX_POINTS,
            overdue_now_max_points=config.OVERDUE_NOW_MAX_POINTS,
            oldest_overdue_cap_days=config.OLDEST_OVERDUE_CAP_DAYS,
            utilisation_max_points=config.UTILISATION_MAX_POINTS,
            utilisation_start_ratio=config.UTILISATION_START_RATIO,
            utilisation_full_ratio=config.UTILISATION_FULL_RATIO,
            reliable_score_upper_bound=config.RELIABLE_SCORE_UPPER_BOUND,
            watch_score_upper_bound=config.WATCH_SCORE_UPPER_BOUND,
            risk_score_min=config.RISK_SCORE_MIN,
            risk_score_max=config.RISK_SCORE_MAX,
            trend_window_days=config.TREND_WINDOW_DAYS,
            trend_min_settled_invoices_per_window=config.TREND_MIN_SETTLED_INVOICES_PER_WINDOW,
            reliable_peak_outstanding_multiplier=config.RELIABLE_PEAK_OUTSTANDING_MULTIPLIER,
            risky_current_limit_multiplier=config.RISKY_CURRENT_LIMIT_MULTIPLIER,
            credit_limit_rounding_increment=config.CREDIT_LIMIT_ROUNDING_INCREMENT,
            next_5_weeks_count=config.CASH_PROJECTION_WEEKS,
            next_5_weeks_days_per_week=config.CASH_PROJECTION_DAYS_PER_WEEK,
            next_5_weeks_horizon_days=(
                config.CASH_PROJECTION_WEEKS * config.CASH_PROJECTION_DAYS_PER_WEEK
            ),
            projection_median_days_late_cap=config.PROJECTION_MEDIAN_DAYS_LATE_CAP,
        ),
    )


def _invoices_by_customer(inputs: AnalyticsInputs) -> dict[int, tuple]:
    grouped: dict[int, list] = {}
    for invoice in inputs.invoices:
        grouped.setdefault(invoice.customer_id, []).append(invoice)
    return {customer_id: tuple(rows) for customer_id, rows in grouped.items()}


@router.get(
    "/receivables",
    response_model=ReceivablesReportResponse,
    dependencies=[Depends(require_permission("reports:read"))],
)
def get_receivables_report(
    report_today: date = Depends(get_reports_today),
    db: Session = Depends(get_db),
):
    """Return portfolio and per-customer open receivables and D24 aging."""
    inputs = load_report_inputs(db)
    portfolio = calculate_receivables_totals(
        inputs.customers, inputs.invoices, inputs.payments, report_today
    )
    invoices_by_customer = _invoices_by_customer(inputs)
    customers = []
    for customer in inputs.customers:
        customer_totals = calculate_receivables_totals(
            (customer,), invoices_by_customer.get(customer.customer_id, ()), inputs.payments, report_today
        )
        customers.append(
            {
                "customer_id": customer.customer_id,
                "customer_name": customer.customer_name,
                "credit_balance": customer.credit_balance,
                "outstanding": customer_totals.total_outstanding,
                "overdue": customer_totals.total_overdue,
                "aging": asdict(customer_totals.aging),
                "reasons": list(customer_totals.reasons),
            }
        )
    return {
        "as_of_date": report_today,
        "totals": {
            "total_outstanding": portfolio.total_outstanding,
            "total_overdue": portfolio.total_overdue,
            "total_customer_credit_balance": portfolio.total_customer_credit_balance,
            "aging": asdict(portfolio.aging),
            "reasons": list(portfolio.reasons),
        },
        "customers": customers,
        "methodology": _methodology(),
    }


@router.get(
    "/customer-risk",
    response_model=CustomerRiskReportResponse,
    dependencies=[Depends(require_permission("reports:read"))],
)
def get_customer_risk_report(
    report_today: date = Depends(get_reports_today),
    db: Session = Depends(get_db),
):
    """Return every customer's D25 risk, explainers, and D26 suggestion."""
    inputs = load_report_inputs(db)
    customer_risks = []
    for customer in inputs.customers:
        risk = calculate_customer_risk(
            customer, inputs.invoices, inputs.payments, report_today
        )
        customer_risks.append(
            {
                "customer_id": risk.customer_id,
                "customer_name": risk.customer_name,
                "credit_balance": customer.credit_balance,
                "score": risk.score,
                "band": risk.band,
                "trend": risk.trend,
                "trend_recent_invoice_count": risk.trend_recent_invoice_count,
                "trend_previous_invoice_count": risk.trend_previous_invoice_count,
                "trend_recent_average_days_late": risk.trend_recent_average_days_late,
                "trend_previous_average_days_late": risk.trend_previous_average_days_late,
                "open_outstanding": risk.components.current_outstanding,
                "open_overdue": risk.aging.total_overdue,
                "aging": asdict(risk.aging),
                "components": asdict(risk.components),
                "suggested_credit_limit": asdict(risk.suggested_credit_limit),
                "reasons": list(risk.reasons),
            }
        )
    return {
        "as_of_date": report_today,
        "customers": customer_risks,
        "methodology": _methodology(),
    }


@router.get(
    "/cash-flow",
    response_model=CashFlowReportResponse,
    dependencies=[Depends(require_permission("reports:read"))],
)
def get_cash_flow_report(
    opening_balance: float | None = Query(
        default=None,
        ge=-1e12,
        le=1e12,
        allow_inf_nan=False,
        description="Optional display-only opening balance; it is never stored.",
    ),
    report_today: date = Depends(get_reports_today),
    db: Session = Depends(get_db),
):
    """Return expected cash movement for the next 5 weeks."""
    inputs = load_report_inputs(db)
    projection = calculate_cash_projection(
        inputs.customers,
        inputs.invoices,
        inputs.payments,
        inputs.suppliers,
        inputs.purchases,
        inputs.supplier_payments,
        report_today,
        opening_balance=opening_balance,
    )
    return {
        "as_of_date": report_today,
        "next_5_weeks": {
            "opening_balance": projection.opening_balance,
            "weeks": [asdict(week) for week in projection.weeks],
            "projected_invoice_receipts": [
                asdict(receipt) for receipt in projection.projected_invoice_receipts
            ],
            "projected_purchase_outflows": [
                asdict(outflow) for outflow in projection.projected_purchase_outflows
            ],
            "reasons": list(projection.reasons),
        },
        "methodology": _methodology(),
    }
