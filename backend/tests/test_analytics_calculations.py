"""Offline unit tests for the pure Cash & Credit Intelligence calculations."""

from __future__ import annotations

from datetime import date, timedelta
import unittest

from app.scripts.demo_personas import PERSONAS
from app.scripts.seed_demo import build_plan
from app.services.analytics.calculations import (
    calculate_aging,
    calculate_cash_projection,
    calculate_customer_risk,
    calculate_invoice_analysis,
    calculate_receivables_totals,
)
from app.services.analytics.models import (
    CustomerInput,
    InvoiceInput,
    PaymentInput,
    PurchaseInput,
    SupplierInput,
    SupplierPaymentInput,
)


TODAY = date(2026, 10, 22)


def customer(
    customer_id: int = 1,
    *,
    credit_limit: float = 10_000,
    credit_balance: float = 0,
    payment_terms_days: int = 10,
) -> CustomerInput:
    return CustomerInput(
        customer_id=customer_id,
        customer_name=f"Customer {customer_id}",
        credit_limit=credit_limit,
        credit_balance=credit_balance,
        payment_terms_days=payment_terms_days,
    )


def invoice(
    invoice_id: int,
    customer_id: int,
    invoice_date: date,
    amount: float = 100,
    status: str = "UNPAID",
) -> InvoiceInput:
    return InvoiceInput(
        invoice_id=invoice_id,
        customer_id=customer_id,
        invoice_date=invoice_date,
        total_amount=amount,
        status=status,
    )


def payment(
    payment_id: int,
    invoice_id: int,
    payment_date: date,
    amount: float,
    method: str = "CASH",
) -> PaymentInput:
    return PaymentInput(
        payment_id=payment_id,
        invoice_id=invoice_id,
        payment_date=payment_date,
        amount=amount,
        payment_method=method,
    )


class InvoiceAndReceivablesTests(unittest.TestCase):
    def test_credit_rows_reduce_behaviour_owed_but_are_not_real_payment_behaviour(self):
        row = invoice(1, 1, TODAY - timedelta(days=20))
        analysis = calculate_invoice_analysis(
            row,
            customer(),
            (
                payment(1, 1, TODAY - timedelta(days=12), 30, "RETURN_CREDIT"),
                payment(2, 1, TODAY - timedelta(days=8), 70, "BANK_TRANSFER"),
            ),
            TODAY,
        )

        self.assertIsNotNone(analysis)
        assert analysis is not None
        self.assertEqual(analysis.credit_payment_amount, 30)
        self.assertEqual(analysis.real_payment_amount, 70)
        self.assertEqual(analysis.behaviour_owed_amount, 70)
        self.assertEqual(analysis.remaining_amount, 0)
        self.assertEqual(analysis.settlement_date, TODAY - timedelta(days=8))
        self.assertEqual(analysis.days_late, 2)
        self.assertIn("credit and 70.00 real", analysis.reasons[1])

    def test_invoice_fully_covered_by_credit_is_excluded_from_lateness(self):
        row = invoice(1, 1, TODAY - timedelta(days=40))
        analysis = calculate_invoice_analysis(
            row,
            customer(),
            (payment(1, 1, TODAY - timedelta(days=30), 100, "CREDIT_APPLIED"),),
            TODAY,
        )

        self.assertIsNotNone(analysis)
        assert analysis is not None
        self.assertTrue(analysis.excluded_from_lateness)
        self.assertIsNone(analysis.settlement_date)
        self.assertIsNone(analysis.days_late)
        self.assertFalse(analysis.is_open)

    def test_partial_payment_uses_all_payment_rows_for_open_balance_and_aging(self):
        row = invoice(1, 1, TODAY - timedelta(days=40))
        analysis = calculate_invoice_analysis(
            row,
            customer(),
            (payment(1, 1, TODAY - timedelta(days=15), 75),),
            TODAY,
        )

        self.assertIsNotNone(analysis)
        assert analysis is not None
        self.assertTrue(analysis.is_open)
        self.assertEqual(analysis.remaining_amount, 25)
        self.assertEqual(analysis.overdue_days, 30)
        aging = calculate_aging((analysis,))
        self.assertEqual(aging.days_1_30, 25)
        self.assertEqual(aging.total_overdue, 25)

    def test_aging_uses_each_open_balance_bucket_and_keeps_credit_separate(self):
        rows = (
            invoice(1, 1, TODAY - timedelta(days=5), 10),
            invoice(2, 1, TODAY - timedelta(days=20), 20),
            invoice(3, 1, TODAY - timedelta(days=50), 30),
            invoice(4, 1, TODAY - timedelta(days=80), 40),
            invoice(5, 1, TODAY - timedelta(days=110), 50),
        )
        c = customer(credit_balance=99, payment_terms_days=10)
        totals = calculate_receivables_totals((c,), rows, (), TODAY)

        self.assertEqual(totals.aging.not_yet_due, 10)
        self.assertEqual(totals.aging.days_1_30, 20)
        self.assertEqual(totals.aging.days_31_60, 30)
        self.assertEqual(totals.aging.days_61_90, 40)
        self.assertEqual(totals.aging.days_90_plus, 50)
        self.assertEqual(totals.total_outstanding, 150)
        self.assertEqual(totals.total_overdue, 140)
        self.assertEqual(totals.total_customer_credit_balance, 99)

    def test_cancelled_invoice_is_ignored_everywhere(self):
        c = customer()
        cancelled = invoice(1, 1, TODAY - timedelta(days=100), 500, "CANCELLED")
        live = invoice(2, 1, TODAY - timedelta(days=5), 100)
        totals = calculate_receivables_totals((c,), (cancelled, live), (), TODAY)

        self.assertEqual(len(totals.invoice_analyses), 1)
        self.assertEqual(totals.total_outstanding, 100)


class RiskTests(unittest.TestCase):
    def test_insufficient_history_returns_no_score_but_preserves_open_aging(self):
        c = customer()
        settled = (
            invoice(1, 1, TODAY - timedelta(days=50)),
            invoice(2, 1, TODAY - timedelta(days=40)),
        )
        payments = (
            payment(1, 1, TODAY - timedelta(days=40), 100),
            payment(2, 2, TODAY - timedelta(days=30), 100),
        )
        open_invoice = invoice(3, 1, TODAY - timedelta(days=45), 250)
        risk = calculate_customer_risk(c, (*settled, open_invoice), payments, TODAY)

        self.assertEqual(risk.band, "INSUFFICIENT_HISTORY")
        self.assertIsNone(risk.score)
        self.assertEqual(risk.aging.days_31_60, 250)
        self.assertIsNone(risk.suggested_credit_limit.suggested_limit)
        self.assertTrue(any(reason.startswith("Not enough history") for reason in risk.reasons))

    def test_zero_credit_limit_has_zero_utilisation_component_and_reason(self):
        c = customer(credit_limit=0)
        rows = tuple(invoice(index, 1, TODAY - timedelta(days=30 + index)) for index in range(1, 4))
        payments = tuple(
            payment(index, index, TODAY - timedelta(days=20 + index), 100)
            for index in range(1, 4)
        )
        risk = calculate_customer_risk(c, rows, payments, TODAY)

        self.assertEqual(risk.band, "RELIABLE")
        self.assertEqual(risk.components.utilisation_points, 0)
        self.assertIsNone(risk.components.utilisation_ratio)
        self.assertTrue(any(reason.startswith("No credit limit set") for reason in risk.reasons))

    def test_trend_requires_two_settled_invoices_in_each_window(self):
        c = customer()
        rows = (
            invoice(1, 1, TODAY - timedelta(days=180)),
            invoice(2, 1, TODAY - timedelta(days=170)),
            invoice(3, 1, TODAY - timedelta(days=20)),
        )
        payments = (
            payment(1, 1, TODAY - timedelta(days=160), 100),
            payment(2, 2, TODAY - timedelta(days=150), 100),
            payment(3, 3, TODAY - timedelta(days=10), 100),
        )
        risk = calculate_customer_risk(c, rows, payments, TODAY)

        self.assertIsNone(risk.trend)
        self.assertEqual(risk.trend_previous_invoice_count, 2)
        self.assertEqual(risk.trend_recent_invoice_count, 1)
        self.assertIn("need 2 settled invoices", risk.reasons[-1])

    def test_credit_limit_suggestions_follow_reliable_and_risky_formulas(self):
        reliable_customer = customer(credit_limit=1_000)
        reliable_rows = (
            invoice(1, 1, TODAY - timedelta(days=160), 2_000),
            invoice(2, 1, TODAY - timedelta(days=120), 2_000),
            invoice(3, 1, TODAY - timedelta(days=80), 2_000),
        )
        reliable_payments = (
            payment(1, 1, TODAY - timedelta(days=150), 2_000),
            payment(2, 2, TODAY - timedelta(days=110), 2_000),
            payment(3, 3, TODAY - timedelta(days=70), 2_000),
        )
        reliable = calculate_customer_risk(
            reliable_customer, reliable_rows, reliable_payments, TODAY
        )
        self.assertEqual(reliable.band, "RELIABLE")
        self.assertEqual(reliable.suggested_credit_limit.suggested_limit, 3_000)

        risky_customer = customer(credit_limit=10_000)
        risky_rows = tuple(
            invoice(index, 1, TODAY - timedelta(days=100 + index), 100)
            for index in range(1, 4)
        ) + (invoice(4, 1, TODAY - timedelta(days=40), 5_500),)
        risky_payments = tuple(
            payment(index, index, TODAY - timedelta(days=40 + index), 100)
            for index in range(1, 4)
        )
        risky = calculate_customer_risk(risky_customer, risky_rows, risky_payments, TODAY)
        self.assertEqual(risky.band, "RISKY")
        self.assertEqual(risky.suggested_credit_limit.suggested_limit, 6_000)
        self.assertGreaterEqual(
            risky.suggested_credit_limit.suggested_limit or 0,
            risky.components.current_outstanding,
        )


class CashProjectionTests(unittest.TestCase):
    def test_purchase_already_overdue_is_projected_out_today_after_partial_payment(self):
        supplier = SupplierInput(1, "Supplier", 10)
        purchase = PurchaseInput(1, 1, TODAY - timedelta(days=20), 1_000, "RECEIVED")
        cancelled_purchase = PurchaseInput(2, 1, TODAY - timedelta(days=20), 900, "CANCELLED")
        supplier_payment = SupplierPaymentInput(1, 1, TODAY - timedelta(days=5), 400)
        projection = calculate_cash_projection(
            (customer(),),
            (),
            (),
            (supplier,),
            (purchase, cancelled_purchase),
            (supplier_payment,),
            TODAY,
            opening_balance=500,
        )

        first_week = projection.weeks[0]
        self.assertEqual(first_week.expected_out, 600)
        self.assertEqual(first_week.net_movement, -600)
        self.assertEqual(first_week.cumulative_net, -600)
        self.assertEqual(first_week.projected_balance, -100)
        self.assertEqual(len(projection.projected_purchase_outflows), 1)
        self.assertEqual(projection.projected_purchase_outflows[0].expected_date, TODAY)

    def test_receipt_projection_uses_median_lateness_and_conservative_excludes_risky(self):
        c = customer(credit_limit=1_000)
        settled_rows = (
            invoice(1, 1, TODAY - timedelta(days=100), 100),
            invoice(2, 1, TODAY - timedelta(days=90), 100),
            invoice(3, 1, TODAY - timedelta(days=80), 100),
        )
        settled_payments = (
            payment(1, 1, TODAY - timedelta(days=70), 100),
            payment(2, 2, TODAY - timedelta(days=60), 100),
            payment(3, 3, TODAY - timedelta(days=50), 100),
        )
        open_row = invoice(4, 1, TODAY - timedelta(days=20), 1_000)
        projection = calculate_cash_projection(
            (c,),
            (*settled_rows, open_row),
            settled_payments,
            (),
            (),
            (),
            TODAY,
        )

        receipt = projection.projected_invoice_receipts[0]
        self.assertEqual(receipt.median_days_late, 20)
        self.assertEqual(receipt.expected_date, TODAY + timedelta(days=20))
        self.assertEqual(receipt.customer_band, "RISKY")
        self.assertFalse(receipt.included_in_conservative_series)
        self.assertEqual(projection.weeks[2].expected_in, 1_000)
        self.assertEqual(projection.weeks[2].conservative_expected_in, 0)

    def test_receipt_projection_uses_zero_lateness_when_history_is_insufficient(self):
        c = customer()
        open_row = invoice(1, 1, TODAY - timedelta(days=20), 500)
        projection = calculate_cash_projection(
            (c,), (open_row,), (), (), (), (), TODAY
        )

        receipt = projection.projected_invoice_receipts[0]
        self.assertEqual(receipt.median_days_late, 0)
        self.assertEqual(receipt.expected_date, TODAY)
        self.assertEqual(receipt.week_number, 1)


class DemoPersonaAnalyticsTests(unittest.TestCase):
    def test_demo_plan_personas_match_their_shared_expected_bands_and_trends(self):
        plan = build_plan(seed=42, months=12, today=TODAY)
        customers, invoices, payments = self._convert_plan_to_analytics_rows(plan)
        risks = {
            row.customer_name: calculate_customer_risk(row, invoices, payments, TODAY)
            for row in customers
        }
        expected_suggestions = {
            "RELIABLE": 30_000,
            "CHRONICALLY_LATE": 10_000,
            "WORSENING": 30_000,
            "NEAR_LIMIT": 10_000,
            "NEW": None,
            "CREDIT_HOLDER": 25_000,
        }

        for persona in PERSONAS:
            with self.subTest(persona=persona.key):
                risk = risks[persona.customer_name]
                self.assertEqual(risk.band, persona.expected_band)
                self.assertEqual(risk.trend, persona.expected_trend)
                self.assertEqual(
                    risk.suggested_credit_limit.suggested_limit,
                    expected_suggestions[persona.key],
                )

    @staticmethod
    def _convert_plan_to_analytics_rows(plan):
        customer_ids = {}
        invoice_ids = {}
        customers = []
        invoices = []
        payments = []
        next_customer_id = 1
        next_invoice_id = 1
        next_payment_id = 1

        for event in plan.events:
            if event.entity == "customer" and event.operation == "create":
                customer_ids[event.result_ref] = next_customer_id
                customers.append(
                    CustomerInput(
                        customer_id=next_customer_id,
                        customer_name=event.payload["customer_name"],
                        credit_limit=event.payload["credit_limit"],
                        credit_balance=0,
                        payment_terms_days=event.payload["payment_terms_days"],
                    )
                )
                next_customer_id += 1
            elif event.entity == "invoice" and event.operation == "create":
                # Demo order and customer references differ after the persona key;
                # the event's persona key is the canonical connection in the pure plan.
                customer_ref = f"customer:{event.persona_key}"
                invoice_ids[event.result_ref] = next_invoice_id
                invoices.append(
                    InvoiceInput(
                        invoice_id=next_invoice_id,
                        customer_id=customer_ids[customer_ref],
                        invoice_date=event.payload["invoice_date"],
                        total_amount=event.payload["total_amount"],
                        status=event.payload["status"],
                    )
                )
                next_invoice_id += 1
            elif event.entity == "payment" and event.operation == "create":
                payments.append(
                    PaymentInput(
                        payment_id=next_payment_id,
                        invoice_id=invoice_ids[event.payload["invoice_id"]["$ref"]],
                        payment_date=event.payload["payment_date"],
                        amount=event.payload["amount"],
                        payment_method=event.payload["payment_method"],
                    )
                )
                next_payment_id += 1
        return tuple(customers), tuple(invoices), tuple(payments)


if __name__ == "__main__":
    unittest.main()
