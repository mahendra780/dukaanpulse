"""Pure, explainable calculations for Cash & Credit Intelligence (D24--D27)."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from math import ceil
from statistics import median
from typing import Iterable, Sequence

from app.services.analytics import config
from app.services.analytics.models import (
    AgingBuckets,
    CashProjection,
    CashProjectionWeek,
    CreditLimitSuggestion,
    CustomerInput,
    CustomerRisk,
    InvoiceAnalysis,
    InvoiceInput,
    PaymentInput,
    ProjectedInvoiceReceipt,
    ProjectedPurchaseOutflow,
    PurchaseInput,
    ReceivablesTotals,
    RiskComponents,
    SupplierInput,
    SupplierPaymentInput,
)


CREDIT_PAYMENT_METHODS = frozenset({"RETURN_CREDIT", "CREDIT_APPLIED"})
REAL_PAYMENT_METHODS = frozenset({"CASH", "UPI", "BANK_TRANSFER", "CHEQUE"})
_AMOUNT_EPSILON = 0.000001


def calculate_invoice_analysis(
    invoice: InvoiceInput,
    customer: CustomerInput,
    payments: Iterable[PaymentInput],
    today: date,
) -> InvoiceAnalysis | None:
    """Return the D24 state of an invoice as at ``today``.

    Cancelled invoices and invoices dated after the requested snapshot are
    ignored.  Payments dated after the snapshot are likewise excluded, which
    keeps this function valid for historical as-of reporting as well as today.
    """
    if _is_cancelled(invoice.status) or invoice.invoice_date > today:
        return None
    if invoice.customer_id != customer.customer_id:
        raise ValueError("Invoice customer does not match the supplied customer.")

    relevant_payments = sorted(
        (
            payment
            for payment in payments
            if payment.invoice_id == invoice.invoice_id and payment.payment_date <= today
        ),
        key=lambda payment: (payment.payment_date, payment.payment_id),
    )
    credit_payments = [
        payment
        for payment in relevant_payments
        if payment.payment_method.upper() in CREDIT_PAYMENT_METHODS
    ]
    real_payments = [
        payment
        for payment in relevant_payments
        if payment.payment_method.upper() in REAL_PAYMENT_METHODS
    ]
    credit_total = _money(sum(payment.amount for payment in credit_payments))
    real_total = _money(sum(payment.amount for payment in real_payments))
    all_payment_total = _money(sum(payment.amount for payment in relevant_payments))
    behaviour_owed = _non_negative(invoice.total_amount - credit_total)
    remaining = _non_negative(invoice.total_amount - all_payment_total)
    due_date = invoice.invoice_date + timedelta(days=customer.payment_terms_days)

    excluded_from_lateness = behaviour_owed <= _AMOUNT_EPSILON
    settlement_date: date | None = None
    if not excluded_from_lateness:
        cumulative_real = 0.0
        for payment in real_payments:
            cumulative_real += payment.amount
            if cumulative_real + _AMOUNT_EPSILON >= behaviour_owed:
                settlement_date = payment.payment_date
                break

    days_late = (
        max(0, (settlement_date - due_date).days)
        if settlement_date is not None
        else None
    )
    is_open = remaining > _AMOUNT_EPSILON
    overdue_days = max(0, (today - due_date).days) if is_open else 0

    reasons = [
        f"Due on {due_date.isoformat()} after {customer.payment_terms_days} payment-term days.",
        (
            f"Payments total {_format_amount(all_payment_total)}: "
            f"{_format_amount(credit_total)} credit and {_format_amount(real_total)} real."
        ),
    ]
    if excluded_from_lateness:
        reasons.append(
            "Credit rows cover the full invoice, so it is excluded from payment-behaviour lateness."
        )
    elif settlement_date is not None:
        reasons.append(
            f"Real payments reached {_format_amount(behaviour_owed)} on {settlement_date.isoformat()}, "
            f"{days_late} days late."
        )
    else:
        reasons.append(
            f"Real payments have not reached {_format_amount(behaviour_owed)} for payment-behaviour settlement."
        )
    if is_open:
        reasons.append(
            f"Open remaining balance is {_format_amount(remaining)} and is {overdue_days} days past due."
        )
    else:
        reasons.append("No remaining balance is open.")

    return InvoiceAnalysis(
        invoice_id=invoice.invoice_id,
        customer_id=invoice.customer_id,
        invoice_date=invoice.invoice_date,
        due_date=due_date,
        total_amount=_money(invoice.total_amount),
        credit_payment_amount=credit_total,
        real_payment_amount=real_total,
        total_payment_amount=all_payment_total,
        behaviour_owed_amount=_money(behaviour_owed),
        remaining_amount=_money(remaining),
        settlement_date=settlement_date,
        days_late=days_late,
        overdue_days=overdue_days,
        is_open=is_open,
        excluded_from_lateness=excluded_from_lateness,
        reasons=tuple(reasons),
    )


def calculate_invoice_analyses(
    customers: Iterable[CustomerInput],
    invoices: Iterable[InvoiceInput],
    payments: Iterable[PaymentInput],
    today: date,
) -> tuple[InvoiceAnalysis, ...]:
    """Calculate D24 state for every non-cancelled invoice in one pure pass."""
    customers_by_id = {customer.customer_id: customer for customer in customers}
    payments_by_invoice: dict[int, list[PaymentInput]] = defaultdict(list)
    for payment in payments:
        payments_by_invoice[payment.invoice_id].append(payment)

    analyses: list[InvoiceAnalysis] = []
    for invoice in invoices:
        customer = customers_by_id.get(invoice.customer_id)
        if customer is None:
            raise ValueError(f"Invoice {invoice.invoice_id} has no analytics customer input.")
        analysis = calculate_invoice_analysis(
            invoice,
            customer,
            payments_by_invoice[invoice.invoice_id],
            today,
        )
        if analysis is not None:
            analyses.append(analysis)
    return tuple(sorted(analyses, key=lambda analysis: analysis.invoice_id))


def calculate_aging(invoice_analyses: Iterable[InvoiceAnalysis]) -> AgingBuckets:
    """Put each D24 open remaining balance into exactly one aging bucket."""
    not_yet_due = 0.0
    days_1_30 = 0.0
    days_31_60 = 0.0
    days_61_90 = 0.0
    days_90_plus = 0.0
    open_count = 0

    for analysis in invoice_analyses:
        if not analysis.is_open:
            continue
        open_count += 1
        if analysis.overdue_days == 0:
            not_yet_due += analysis.remaining_amount
        elif analysis.overdue_days <= config.AGING_1_30_MAX_DAYS:
            days_1_30 += analysis.remaining_amount
        elif analysis.overdue_days <= config.AGING_31_60_MAX_DAYS:
            days_31_60 += analysis.remaining_amount
        elif analysis.overdue_days <= config.AGING_61_90_MAX_DAYS:
            days_61_90 += analysis.remaining_amount
        else:
            days_90_plus += analysis.remaining_amount

    total_open = _money(not_yet_due + days_1_30 + days_31_60 + days_61_90 + days_90_plus)
    total_overdue = _money(days_1_30 + days_31_60 + days_61_90 + days_90_plus)
    return AgingBuckets(
        not_yet_due=_money(not_yet_due),
        days_1_30=_money(days_1_30),
        days_31_60=_money(days_31_60),
        days_61_90=_money(days_61_90),
        days_90_plus=_money(days_90_plus),
        total_open=total_open,
        total_overdue=total_overdue,
        reasons=(
            f"{open_count} open invoice(s) total {_format_amount(total_open)}.",
            f"{_format_amount(total_overdue)} is overdue; customer credit balances are not netted against it.",
        ),
    )


def calculate_receivables_totals(
    customers: Iterable[CustomerInput],
    invoices: Iterable[InvoiceInput],
    payments: Iterable[PaymentInput],
    today: date,
) -> ReceivablesTotals:
    """Return explainable portfolio receivables totals without netting credit."""
    customer_rows = tuple(customers)
    analyses = calculate_invoice_analyses(customer_rows, invoices, payments, today)
    aging = calculate_aging(analyses)
    credit_balance = _money(sum(customer.credit_balance for customer in customer_rows))
    return ReceivablesTotals(
        total_outstanding=aging.total_open,
        total_overdue=aging.total_overdue,
        total_customer_credit_balance=credit_balance,
        aging=aging,
        invoice_analyses=analyses,
        reasons=(
            f"Open receivables total {_format_amount(aging.total_open)}.",
            f"Overdue receivables total {_format_amount(aging.total_overdue)}.",
            f"Customer credit we owe totals {_format_amount(credit_balance)} and is shown separately.",
        ),
    )


def calculate_customer_risk(
    customer: CustomerInput,
    invoices: Iterable[InvoiceInput],
    payments: Iterable[PaymentInput],
    today: date,
) -> CustomerRisk:
    """Calculate the transparent D25 risk score, trend, and D26 suggestion."""
    invoice_rows = tuple(
        invoice for invoice in invoices if invoice.customer_id == customer.customer_id
    )
    payment_rows = tuple(payments)
    analyses = calculate_invoice_analyses((customer,), invoice_rows, payment_rows, today)
    aging = calculate_aging(analyses)
    history = _risk_history(analyses, today)
    oldest_overdue_days = max(
        (analysis.overdue_days for analysis in analyses if analysis.is_open),
        default=0,
    )
    current_outstanding = aging.total_open
    late_count = sum((analysis.days_late or 0) > 0 for analysis in history)
    average_days_late = (
        sum(analysis.days_late or 0 for analysis in history) / len(history)
        if history
        else None
    )
    late_share = late_count / len(history) if history else None
    utilisation_ratio = (
        current_outstanding / customer.credit_limit
        if customer.credit_limit > _AMOUNT_EPSILON
        else None
    )

    reasons = [
        f"{len(history)} settled invoice(s) fall in the last {config.RISK_HISTORY_WINDOW_DAYS} days; "
        f"need {config.RISK_MIN_SETTLED_INVOICES} for a risk score.",
    ]
    if history:
        reasons.append(
            f"Paid {late_count} of {len(history)} invoices late "
            f"(avg {average_days_late:.1f} days)."
        )
    if oldest_overdue_days:
        reasons.append(
            f"Oldest open overdue invoice is {oldest_overdue_days} days past due; "
            f"open receivables are {_format_amount(current_outstanding)}."
        )
    else:
        reasons.append(f"No open invoice is overdue; open receivables are {_format_amount(current_outstanding)}.")
    if utilisation_ratio is None:
        reasons.append("No credit limit set; utilisation component is 0 points.")
    else:
        reasons.append(
            f"Credit utilisation is {utilisation_ratio * 100:.1f}% of "
            f"{_format_amount(customer.credit_limit)}."
        )

    if len(history) < config.RISK_MIN_SETTLED_INVOICES:
        components = RiskComponents(
            settled_invoice_count=len(history),
            late_invoice_count=late_count,
            average_days_late=average_days_late,
            late_payment_share=late_share,
            oldest_overdue_days=oldest_overdue_days,
            current_outstanding=current_outstanding,
            credit_limit=_money(customer.credit_limit),
            utilisation_ratio=utilisation_ratio,
            lateness_points=None,
            frequency_points=None,
            overdue_now_points=None,
            utilisation_points=None,
        )
        band = "INSUFFICIENT_HISTORY"
        score = None
        reasons.append(
            "Not enough history to calculate a risk score; open overdue and aging remain available."
        )
    else:
        lateness_points = config.LATENESS_MAX_POINTS * min(
            average_days_late or 0.0, config.LATENESS_CAP_DAYS
        ) / config.LATENESS_CAP_DAYS
        frequency_points = config.LATE_FREQUENCY_MAX_POINTS * (late_share or 0.0)
        overdue_now_points = config.OVERDUE_NOW_MAX_POINTS * min(
            oldest_overdue_days, config.OLDEST_OVERDUE_CAP_DAYS
        ) / config.OLDEST_OVERDUE_CAP_DAYS
        utilisation_points = 0.0
        if utilisation_ratio is not None:
            utilisation_points = config.UTILISATION_MAX_POINTS * _clamp(
                (utilisation_ratio - config.UTILISATION_START_RATIO)
                / (config.UTILISATION_FULL_RATIO - config.UTILISATION_START_RATIO),
                0.0,
                1.0,
            )
        score = _clamp(
            lateness_points + frequency_points + overdue_now_points + utilisation_points,
            config.RISK_SCORE_MIN,
            config.RISK_SCORE_MAX,
        )
        band = _band_for_score(score)
        components = RiskComponents(
            settled_invoice_count=len(history),
            late_invoice_count=late_count,
            average_days_late=average_days_late,
            late_payment_share=late_share,
            oldest_overdue_days=oldest_overdue_days,
            current_outstanding=current_outstanding,
            credit_limit=_money(customer.credit_limit),
            utilisation_ratio=utilisation_ratio,
            lateness_points=lateness_points,
            frequency_points=frequency_points,
            overdue_now_points=overdue_now_points,
            utilisation_points=utilisation_points,
        )
        reasons.append(
            f"Risk score {score:.1f} = {lateness_points:.1f} lateness + "
            f"{frequency_points:.1f} frequency + {overdue_now_points:.1f} overdue-now + "
            f"{utilisation_points:.1f} utilisation: {band}."
        )

    trend, recent, previous, trend_reason = _calculate_trend(analyses, today)
    reasons.append(trend_reason)
    peak_outstanding = _peak_outstanding_last_180_days(
        customer.customer_id,
        invoice_rows,
        payment_rows,
        today,
    )
    suggestion = _calculate_credit_limit_suggestion(
        band=band,
        current_limit=customer.credit_limit,
        current_outstanding=current_outstanding,
        peak_outstanding=peak_outstanding,
    )

    return CustomerRisk(
        customer_id=customer.customer_id,
        customer_name=customer.customer_name,
        score=score,
        band=band,
        trend=trend,
        trend_recent_invoice_count=len(recent),
        trend_previous_invoice_count=len(previous),
        trend_recent_average_days_late=_average_days_late(recent),
        trend_previous_average_days_late=_average_days_late(previous),
        components=components,
        aging=aging,
        suggested_credit_limit=suggestion,
        reasons=tuple(reasons),
    )


def calculate_cash_projection(
    customers: Iterable[CustomerInput],
    invoices: Iterable[InvoiceInput],
    payments: Iterable[PaymentInput],
    suppliers: Iterable[SupplierInput],
    purchases: Iterable[PurchaseInput],
    supplier_payments: Iterable[SupplierPaymentInput],
    today: date,
    opening_balance: float | None = None,
) -> CashProjection:
    """Return the D27 five-week expected-IN/OUT projection.

    ``opening_balance`` is an optional caller-provided display input only.  It
    is never persisted or inferred; movement and cumulative-net values always
    remain independent of it.
    """
    customer_rows = tuple(customers)
    invoice_rows = tuple(invoices)
    payment_rows = tuple(payments)
    supplier_rows = tuple(suppliers)
    purchase_rows = tuple(purchases)
    supplier_payment_rows = tuple(supplier_payments)

    analyses = calculate_invoice_analyses(customer_rows, invoice_rows, payment_rows, today)
    analyses_by_customer: dict[int, list[InvoiceAnalysis]] = defaultdict(list)
    for analysis in analyses:
        analyses_by_customer[analysis.customer_id].append(analysis)
    risks = {
        customer.customer_id: calculate_customer_risk(
            customer, invoice_rows, payment_rows, today
        )
        for customer in customer_rows
    }
    customer_by_id = {customer.customer_id: customer for customer in customer_rows}
    supplier_by_id = {supplier.supplier_id: supplier for supplier in supplier_rows}

    projected_receipts: list[ProjectedInvoiceReceipt] = []
    for analysis in analyses:
        if not analysis.is_open:
            continue
        customer = customer_by_id[analysis.customer_id]
        history = _risk_history(analyses_by_customer[customer.customer_id], today)
        if len(history) < config.RISK_MIN_SETTLED_INVOICES:
            median_days_late = 0.0
            median_reason = (
                f"Only {len(history)} settled invoice(s) in the last "
                f"{config.RISK_HISTORY_WINDOW_DAYS} days, so median lateness is 0 days."
            )
        else:
            raw_median = float(median(analysis_item.days_late or 0 for analysis_item in history))
            median_days_late = min(raw_median, float(config.PROJECTION_MEDIAN_DAYS_LATE_CAP))
            median_reason = (
                f"Median lateness is {median_days_late:.1f} days from {len(history)} settled invoice(s), "
                f"capped at {config.PROJECTION_MEDIAN_DAYS_LATE_CAP} days."
            )
        scheduled_days_late = ceil(median_days_late)
        expected_date = max(analysis.due_date, today) + timedelta(days=scheduled_days_late)
        week_number = _week_number(expected_date, today)
        risk = risks[customer.customer_id]
        conservative = risk.band != "RISKY"
        receipt_reasons = (
            f"Expected on max(due date {analysis.due_date.isoformat()}, today {today.isoformat()}) "
            f"+ {scheduled_days_late} scheduled median-lateness day(s).",
            median_reason,
            (
                "Included in the conservative series."
                if conservative
                else "Excluded from the conservative series because the customer is RISKY."
            ),
        )
        projected_receipts.append(
            ProjectedInvoiceReceipt(
                invoice_id=analysis.invoice_id,
                customer_id=customer.customer_id,
                customer_name=customer.customer_name,
                remaining_amount=analysis.remaining_amount,
                due_date=analysis.due_date,
                median_days_late=median_days_late,
                scheduled_days_late=scheduled_days_late,
                expected_date=expected_date,
                customer_band=risk.band,
                included_in_conservative_series=conservative,
                week_number=week_number,
                reasons=receipt_reasons,
            )
        )

    payments_by_purchase: dict[int, list[SupplierPaymentInput]] = defaultdict(list)
    for supplier_payment in supplier_payment_rows:
        if supplier_payment.payment_date <= today:
            payments_by_purchase[supplier_payment.purchase_id].append(supplier_payment)
    projected_outflows: list[ProjectedPurchaseOutflow] = []
    for purchase in purchase_rows:
        if _is_cancelled(purchase.status) or purchase.purchase_date > today:
            continue
        supplier = supplier_by_id.get(purchase.supplier_id)
        if supplier is None:
            raise ValueError(f"Purchase {purchase.purchase_id} has no analytics supplier input.")
        paid_amount = sum(
            supplier_payment.amount
            for supplier_payment in payments_by_purchase[purchase.purchase_id]
        )
        remaining = _money(_non_negative(purchase.total_amount - paid_amount))
        if remaining <= _AMOUNT_EPSILON:
            continue
        due_date = purchase.purchase_date + timedelta(days=supplier.payment_terms_days)
        expected_date = max(due_date, today)
        week_number = _week_number(expected_date, today)
        projected_outflows.append(
            ProjectedPurchaseOutflow(
                purchase_id=purchase.purchase_id,
                supplier_id=supplier.supplier_id,
                supplier_name=supplier.supplier_name,
                remaining_amount=remaining,
                due_date=due_date,
                expected_date=expected_date,
                week_number=week_number,
                reasons=(
                    f"Expected on max(purchase due date {due_date.isoformat()}, today {today.isoformat()}).",
                    f"Purchase total {_format_amount(purchase.total_amount)} less payments "
                    f"{_format_amount(paid_amount)} leaves {_format_amount(remaining)}.",
                ),
            )
        )

    weeks = _build_projection_weeks(
        today,
        projected_receipts,
        projected_outflows,
        opening_balance,
    )
    horizon_end = weeks[-1].end_date
    return CashProjection(
        today=today,
        opening_balance=opening_balance,
        weeks=weeks,
        projected_invoice_receipts=tuple(
            sorted(projected_receipts, key=lambda receipt: (receipt.expected_date, receipt.invoice_id))
        ),
        projected_purchase_outflows=tuple(
            sorted(projected_outflows, key=lambda outflow: (outflow.expected_date, outflow.purchase_id))
        ),
        reasons=(
            f"Five weekly buckets run from {today.isoformat()} through {horizon_end.isoformat()}.",
            "Cumulative net starts at zero; any opening balance is caller-provided and not stored.",
            "The conservative series excludes expected IN from customers banded RISKY.",
        ),
    )


def _build_projection_weeks(
    today: date,
    receipts: Sequence[ProjectedInvoiceReceipt],
    outflows: Sequence[ProjectedPurchaseOutflow],
    opening_balance: float | None,
) -> tuple[CashProjectionWeek, ...]:
    cumulative_net = 0.0
    conservative_cumulative_net = 0.0
    weeks: list[CashProjectionWeek] = []
    for week_number in range(1, config.CASH_PROJECTION_WEEKS + 1):
        start_date = today + timedelta(
            days=(week_number - 1) * config.CASH_PROJECTION_DAYS_PER_WEEK
        )
        end_date = start_date + timedelta(days=config.CASH_PROJECTION_DAYS_PER_WEEK - 1)
        weekly_receipts = [receipt for receipt in receipts if receipt.week_number == week_number]
        weekly_outflows = [outflow for outflow in outflows if outflow.week_number == week_number]
        expected_in = _money(sum(receipt.remaining_amount for receipt in weekly_receipts))
        expected_out = _money(sum(outflow.remaining_amount for outflow in weekly_outflows))
        conservative_expected_in = _money(
            sum(
                receipt.remaining_amount
                for receipt in weekly_receipts
                if receipt.included_in_conservative_series
            )
        )
        net_movement = _money(expected_in - expected_out)
        conservative_net_movement = _money(conservative_expected_in - expected_out)
        cumulative_net = _money(cumulative_net + net_movement)
        conservative_cumulative_net = _money(
            conservative_cumulative_net + conservative_net_movement
        )
        excluded_risky_amount = _money(expected_in - conservative_expected_in)
        week_reasons = [
            f"Expected IN {_format_amount(expected_in)} from {len(weekly_receipts)} invoice(s); "
            f"expected OUT {_format_amount(expected_out)} from {len(weekly_outflows)} purchase(s).",
        ]
        if excluded_risky_amount > _AMOUNT_EPSILON:
            week_reasons.append(
                f"Conservative expected IN excludes {_format_amount(excluded_risky_amount)} from RISKY customers."
            )
        weeks.append(
            CashProjectionWeek(
                week_number=week_number,
                start_date=start_date,
                end_date=end_date,
                expected_in=expected_in,
                expected_out=expected_out,
                net_movement=net_movement,
                cumulative_net=cumulative_net,
                conservative_expected_in=conservative_expected_in,
                conservative_net_movement=conservative_net_movement,
                conservative_cumulative_net=conservative_cumulative_net,
                projected_balance=(
                    _money(opening_balance + cumulative_net)
                    if opening_balance is not None
                    else None
                ),
                conservative_projected_balance=(
                    _money(opening_balance + conservative_cumulative_net)
                    if opening_balance is not None
                    else None
                ),
                reasons=tuple(week_reasons),
            )
        )
    return tuple(weeks)


def _risk_history(analyses: Iterable[InvoiceAnalysis], today: date) -> tuple[InvoiceAnalysis, ...]:
    window_start = today - timedelta(days=config.RISK_HISTORY_WINDOW_DAYS)
    return tuple(
        analysis
        for analysis in analyses
        if (
            analysis.settlement_date is not None
            and window_start <= analysis.settlement_date <= today
        )
    )


def _calculate_trend(
    analyses: Iterable[InvoiceAnalysis], today: date
) -> tuple[str | None, tuple[InvoiceAnalysis, ...], tuple[InvoiceAnalysis, ...], str]:
    recent_start = today - timedelta(days=config.TREND_WINDOW_DAYS)
    previous_start = today - timedelta(days=config.TREND_WINDOW_DAYS * 2)
    recent = tuple(
        analysis
        for analysis in analyses
        if analysis.settlement_date is not None and recent_start <= analysis.settlement_date <= today
    )
    previous = tuple(
        analysis
        for analysis in analyses
        if (
            analysis.settlement_date is not None
            and previous_start <= analysis.settlement_date < recent_start
        )
    )
    required = config.TREND_MIN_SETTLED_INVOICES_PER_WINDOW
    if len(recent) < required or len(previous) < required:
        return (
            None,
            recent,
            previous,
            f"Not enough history for trend: need {required} settled invoices in each 90-day window "
            f"(have {len(recent)} recent and {len(previous)} previous).",
        )
    recent_average = _average_days_late(recent) or 0.0
    previous_average = _average_days_late(previous) or 0.0
    if recent_average > previous_average:
        trend = "WORSENING"
    elif recent_average < previous_average:
        trend = "IMPROVING"
    else:
        trend = "STABLE"
    return (
        trend,
        recent,
        previous,
        f"Trend is {trend}: average days late was {recent_average:.1f} in the last 90 days "
        f"and {previous_average:.1f} in the previous 90 days.",
    )


def _calculate_credit_limit_suggestion(
    *,
    band: str,
    current_limit: float,
    current_outstanding: float,
    peak_outstanding: float,
) -> CreditLimitSuggestion:
    current_limit = _money(current_limit)
    current_outstanding = _money(current_outstanding)
    peak_outstanding = _money(peak_outstanding)
    if band == "INSUFFICIENT_HISTORY":
        return CreditLimitSuggestion(
            suggested_limit=None,
            current_limit=current_limit,
            current_outstanding=current_outstanding,
            peak_outstanding_last_180_days=peak_outstanding,
            multiplier=None,
            rounding_increment=None,
            reasons=(
                "No credit-limit suggestion: there is not enough settled-invoice history for a risk band.",
            ),
        )
    if band == "RELIABLE":
        base_amount = max(
            current_limit,
            config.RELIABLE_PEAK_OUTSTANDING_MULTIPLIER * peak_outstanding,
        )
        suggested = _round_up_to_increment(base_amount, config.CREDIT_LIMIT_ROUNDING_INCREMENT)
        return CreditLimitSuggestion(
            suggested_limit=suggested,
            current_limit=current_limit,
            current_outstanding=current_outstanding,
            peak_outstanding_last_180_days=peak_outstanding,
            multiplier=config.RELIABLE_PEAK_OUTSTANDING_MULTIPLIER,
            rounding_increment=config.CREDIT_LIMIT_ROUNDING_INCREMENT,
            reasons=(
                f"RELIABLE formula: max(current limit {_format_amount(current_limit)}, "
                f"{config.RELIABLE_PEAK_OUTSTANDING_MULTIPLIER:.1f} x peak outstanding "
                f"{_format_amount(peak_outstanding)}) rounded up to "
                f"{_format_amount(config.CREDIT_LIMIT_ROUNDING_INCREMENT)} = {_format_amount(suggested)}.",
            ),
        )
    if band == "WATCH":
        return CreditLimitSuggestion(
            suggested_limit=current_limit,
            current_limit=current_limit,
            current_outstanding=current_outstanding,
            peak_outstanding_last_180_days=peak_outstanding,
            multiplier=None,
            rounding_increment=None,
            reasons=(f"WATCH formula: keep the current limit of {_format_amount(current_limit)}.",),
        )
    base_amount = max(
        current_outstanding,
        config.RISKY_CURRENT_LIMIT_MULTIPLIER * current_limit,
    )
    suggested = _round_up_to_increment(base_amount, config.CREDIT_LIMIT_ROUNDING_INCREMENT)
    suggested = max(suggested, current_outstanding)
    return CreditLimitSuggestion(
        suggested_limit=suggested,
        current_limit=current_limit,
        current_outstanding=current_outstanding,
        peak_outstanding_last_180_days=peak_outstanding,
        multiplier=config.RISKY_CURRENT_LIMIT_MULTIPLIER,
        rounding_increment=config.CREDIT_LIMIT_ROUNDING_INCREMENT,
        reasons=(
            f"RISKY formula: max(current outstanding {_format_amount(current_outstanding)}, "
            f"{config.RISKY_CURRENT_LIMIT_MULTIPLIER:.1f} x current limit "
            f"{_format_amount(current_limit)}) rounded up to "
            f"{_format_amount(config.CREDIT_LIMIT_ROUNDING_INCREMENT)} = {_format_amount(suggested)}; "
            "never below current outstanding.",
        ),
    )


def _peak_outstanding_last_180_days(
    customer_id: int,
    invoices: Iterable[InvoiceInput],
    payments: Iterable[PaymentInput],
    today: date,
) -> float:
    """Calculate the highest end-of-day outstanding balance in the D26 window."""
    window_start = today - timedelta(days=config.RISK_HISTORY_WINDOW_DAYS)
    customer_invoices = {
        invoice.invoice_id: invoice
        for invoice in invoices
        if (
            invoice.customer_id == customer_id
            and not _is_cancelled(invoice.status)
            and invoice.invoice_date <= today
        )
    }
    daily_changes: dict[date, float] = defaultdict(float)
    opening_outstanding = 0.0
    for invoice in customer_invoices.values():
        if invoice.invoice_date < window_start:
            opening_outstanding += invoice.total_amount
        else:
            daily_changes[invoice.invoice_date] += invoice.total_amount
    for payment in payments:
        if payment.invoice_id not in customer_invoices or payment.payment_date > today:
            continue
        if payment.payment_date < window_start:
            opening_outstanding -= payment.amount
        else:
            daily_changes[payment.payment_date] -= payment.amount

    balance = max(0.0, opening_outstanding)
    peak = balance
    for event_date in sorted(daily_changes):
        balance = max(0.0, balance + daily_changes[event_date])
        peak = max(peak, balance)
    return _money(peak)


def _week_number(expected_date: date, today: date) -> int | None:
    difference = (expected_date - today).days
    if difference < 0:
        return None
    week_number = difference // config.CASH_PROJECTION_DAYS_PER_WEEK + 1
    return week_number if week_number <= config.CASH_PROJECTION_WEEKS else None


def _average_days_late(analyses: Iterable[InvoiceAnalysis]) -> float | None:
    rows = tuple(analyses)
    if not rows:
        return None
    return sum(analysis.days_late or 0 for analysis in rows) / len(rows)


def _band_for_score(score: float) -> str:
    if score < config.RELIABLE_SCORE_UPPER_BOUND:
        return "RELIABLE"
    if score < config.WATCH_SCORE_UPPER_BOUND:
        return "WATCH"
    return "RISKY"


def _is_cancelled(status: str) -> bool:
    return status.upper() == "CANCELLED"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _non_negative(value: float) -> float:
    return max(0.0, value)


def _money(value: float) -> float:
    return round(value, 2)


def _round_up_to_increment(value: float, increment: float) -> float:
    if value <= 0:
        return 0.0
    return _money(ceil(value / increment) * increment)


def _format_amount(value: float) -> str:
    return f"{value:,.2f}"
