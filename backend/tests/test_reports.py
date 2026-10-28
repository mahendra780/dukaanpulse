"""Offline API and loader tests for Cash & Credit Intelligence reports."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

from fastapi.testclient import TestClient

from app.core.roles import USER_STATUSES
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.main import app
from app.models.user import User
from app.routers import reports
from app.services.analytics.loaders import AnalyticsInputs, load_report_inputs
from app.services.analytics.models import (
    CustomerInput,
    InvoiceInput,
    PaymentInput,
    PurchaseInput,
    SupplierInput,
    SupplierPaymentInput,
)


TODAY = date(2026, 10, 22)


class ListResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class CountingLoaderSession:
    """A no-database session which returns one bulk-query result at a time."""

    def __init__(self, query_results):
        self.query_results = query_results
        self.execute_count = 0

    def execute(self, _statement):
        result = self.query_results[self.execute_count]
        self.execute_count += 1
        return ListResult(result)


class ReportLoaderTests(unittest.TestCase):
    def _load_with_customer_count(self, customer_count: int):
        customer_rows = [
            SimpleNamespace(
                customer_id=index,
                customer_name=f"Customer {index}",
                credit_limit=1_000,
                credit_balance=0,
                payment_terms_days=14,
            )
            for index in range(1, customer_count + 1)
        ]
        session = CountingLoaderSession(
            [
                customer_rows,
                [],
                [
                    SimpleNamespace(
                        payment_id=1,
                        invoice_id=1,
                        payment_date=TODAY,
                        amount=100,
                        payment_method="RETURN_CREDIT",
                    )
                ],
                [],
                [],
                [],
            ]
        )
        return load_report_inputs(session), session.execute_count

    def test_bulk_loader_query_count_does_not_grow_with_customer_count(self):
        one_customer, one_customer_queries = self._load_with_customer_count(1)
        many_customers, many_customer_queries = self._load_with_customer_count(100)

        self.assertEqual(one_customer_queries, 6)
        self.assertEqual(many_customer_queries, 6)
        self.assertEqual(len(one_customer.customers), 1)
        self.assertEqual(len(many_customers.customers), 100)

    def test_bulk_loader_preserves_customer_payment_method_for_credit_rules(self):
        inputs, _query_count = self._load_with_customer_count(1)

        self.assertEqual(inputs.payments[0].payment_method, "RETURN_CREDIT")


class ReportsTodayTests(unittest.TestCase):
    def test_uses_configured_business_timezone_for_the_report_date(self):
        fixed_utc_instant = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)

        with patch.object(reports.settings, "BUSINESS_TIMEZONE", "Asia/Kolkata"):
            report_today = reports.get_reports_today(fixed_utc_instant)

        self.assertEqual(report_today, date(2026, 10, 26))


class ReportsRouterTests(unittest.TestCase):
    def setUp(self):
        self.user = User(
            user_id=1,
            username="Admin",
            full_name="Active Administrator",
            password_hash=hash_password("current-password"),
            role="ADMIN",
            status=USER_STATUSES[0],
            token_version=0,
        )
        self.inputs = AnalyticsInputs(
            customers=(
                CustomerInput(1, "Open Account", 1_000, 50, 10),
                CustomerInput(2, "Settled Account", 2_000, 0, 10),
            ),
            invoices=(
                InvoiceInput(101, 1, TODAY - timedelta(days=20), 100, "UNPAID"),
                InvoiceInput(201, 2, TODAY - timedelta(days=50), 100, "PAID"),
            ),
            payments=(
                PaymentInput(1, 201, TODAY - timedelta(days=30), 100, "BANK_TRANSFER"),
            ),
            suppliers=(SupplierInput(1, "Supplier", 7),),
            purchases=(
                PurchaseInput(1, 1, TODAY - timedelta(days=10), 500, "RECEIVED"),
            ),
            supplier_payments=(
                SupplierPaymentInput(1, 1, TODAY - timedelta(days=5), 100),
            ),
        )
        self.loader_calls = 0
        self.original_loader = reports.load_report_inputs

        def stub_loader(_db):
            self.loader_calls += 1
            return self.inputs

        reports.load_report_inputs = stub_loader

        def override_get_db():
            yield self

        def override_today():
            return TODAY

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[reports.get_reports_today] = override_today
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        reports.load_report_inputs = self.original_loader
        app.dependency_overrides.clear()

    def get(self, model, user_id):
        if model is User and user_id == self.user.user_id:
            return self.user
        return None

    def _headers_for(self, role: str):
        self.user.role = role
        return {"Authorization": f"Bearer {create_access_token(self.user.user_id)}"}

    def _get_as(self, role: str, path: str):
        return self.client.get(path, headers=self._headers_for(role))

    def test_other_roles_are_forbidden_from_every_report(self):
        for role in ("SALES", "WAREHOUSE", "VIEWER"):
            for path in ("/reports/receivables", "/reports/customer-risk", "/reports/cash-flow"):
                with self.subTest(role=role, path=path):
                    response = self._get_as(role, path)
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(
                        response.json(),
                        {"detail": "You don't have permission to do this."},
                    )
        self.assertEqual(self.loader_calls, 0)

    def test_admin_and_accounts_can_read_every_report(self):
        for role in ("ADMIN", "ACCOUNTS"):
            for path in ("/reports/receivables", "/reports/customer-risk", "/reports/cash-flow"):
                with self.subTest(role=role, path=path):
                    response = self._get_as(role, path)
                    self.assertEqual(response.status_code, 200)

    def test_receivables_response_uses_stubbed_loader_and_typed_shape(self):
        response = self._get_as("ADMIN", "/reports/receivables")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.loader_calls, 1)
        payload = response.json()
        self.assertEqual(payload["as_of_date"], TODAY.isoformat())
        self.assertEqual(payload["totals"]["total_outstanding"], 100)
        self.assertEqual(payload["totals"]["total_customer_credit_balance"], 50)
        self.assertEqual(payload["customers"][0]["credit_balance"], 50)
        self.assertIn("formulas", payload["methodology"])
        self.assertEqual(payload["methodology"]["thresholds"]["next_5_weeks_count"], 5)

    def test_customer_risk_response_keeps_credit_and_open_overdue_separate(self):
        response = self._get_as("ACCOUNTS", "/reports/customer-risk")

        self.assertEqual(response.status_code, 200)
        open_customer = response.json()["customers"][0]
        self.assertEqual(open_customer["credit_balance"], 50)
        self.assertEqual(open_customer["open_outstanding"], 100)
        self.assertEqual(open_customer["open_overdue"], 100)
        self.assertIn("suggested_credit_limit", open_customer)
        self.assertIn("components", open_customer)

    def test_cash_flow_response_names_next_5_weeks_and_returns_both_median_values(self):
        response = self._get_as("ADMIN", "/reports/cash-flow?opening_balance=250")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        projection = payload["next_5_weeks"]
        self.assertEqual(len(projection["weeks"]), 5)
        self.assertEqual(projection["opening_balance"], 250)
        receipt = projection["projected_invoice_receipts"][0]
        self.assertIn("median_days_late", receipt)
        self.assertIn("scheduled_days_late", receipt)
        self.assertIn("rounded UP", payload["methodology"]["median_lateness_rule"])

    def _assert_cash_flow_rejects_opening_balance(self, value: str):
        response = self._get_as("ADMIN", f"/reports/cash-flow?opening_balance={value}")

        self.assertEqual(response.status_code, 422)

    def test_cash_flow_rejects_nan_opening_balance(self):
        self._assert_cash_flow_rejects_opening_balance("nan")

    def test_cash_flow_rejects_positive_infinity_opening_balance(self):
        self._assert_cash_flow_rejects_opening_balance("inf")

    def test_cash_flow_rejects_negative_infinity_opening_balance(self):
        self._assert_cash_flow_rejects_opening_balance("-inf")

    def test_cash_flow_rejects_out_of_bounds_opening_balance(self):
        self._assert_cash_flow_rejects_opening_balance("1e30")

    def test_each_report_request_invokes_the_stubbed_bulk_loader_once(self):
        response = self._get_as("ADMIN", "/reports/customer-risk")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.loader_calls, 1)


if __name__ == "__main__":
    unittest.main()
