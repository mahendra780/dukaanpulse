from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app.routers import reports
from tests.auth_test_support import CookieSessionTestCase


class ReportsTodayTests(unittest.TestCase):
    def test_uses_configured_business_timezone_for_the_report_date(self):
        fixed_utc_instant = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)
        with patch.object(reports.settings, "BUSINESS_TIMEZONE", "Asia/Kolkata"):
            self.assertEqual(reports.get_reports_today(fixed_utc_instant).isoformat(), "2026-10-26")


class ReportsRouterTests(CookieSessionTestCase):
    def _authenticate_as(self, role: str):
        user = self.make_user(username=f"{role.lower()}-user", mobile_e164=None)
        _, membership = self.make_workspace_membership(user, role=role)
        self.authenticate_client(user, membership)

    def test_owner_admin_and_accounts_can_read_every_report(self):
        for role in ("OWNER", "ADMIN", "ACCOUNTS"):
            with self.subTest(role=role):
                self.client.cookies.clear()
                self._authenticate_as(role)
                for path in ("/reports/receivables", "/reports/customer-risk", "/reports/cash-flow?opening_balance=250"):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertIn("methodology", response.json())

    def test_other_workspace_roles_are_forbidden_from_every_report(self):
        for role in ("SALES", "WAREHOUSE", "VIEWER"):
            with self.subTest(role=role):
                self.client.cookies.clear()
                self._authenticate_as(role)
                for path in ("/reports/receivables", "/reports/customer-risk", "/reports/cash-flow"):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.json(), {"detail": "You don't have permission to do this."})

    def test_cash_flow_rejects_non_finite_or_out_of_range_opening_balance(self):
        self._authenticate_as("OWNER")
        for value in ("nan", "inf", "-inf", "1e30"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get(f"/reports/cash-flow?opening_balance={value}").status_code, 422)


if __name__ == "__main__":
    unittest.main()
