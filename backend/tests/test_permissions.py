import os
import re
import unittest
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

from fastapi.testclient import TestClient

from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS, permissions_for_role
from app.core.roles import ROLES, USER_STATUSES
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.main import app
from app.models.user import User


SIDEBAR_PAGE_PERMISSIONS = {
    "/": frozenset({"dashboard:read"}),
    "/products": frozenset({"products:read", "categories:read"}),
    "/customers": frozenset({"customers:read"}),
    "/suppliers": frozenset({"suppliers:read"}),
    "/purchases": frozenset({"purchases:read", "suppliers:read", "products:read"}),
    "/orders": frozenset({"orders:read", "customers:read", "products:read"}),
    "/invoices": frozenset({"invoices:read", "orders:read"}),
    "/deliveries": frozenset({"deliveries:read", "invoices:read"}),
    "/payments": frozenset({"payments:read", "invoices:read"}),
    "/purchase-payments": frozenset({"purchase_payments:read", "purchases:read"}),
    "/returns": frozenset({"returns:read", "invoices:read"}),
    "/inventory": frozenset({"inventory:read", "products:read"}),
    "/users": frozenset({"users:manage"}),
}

# GET calls on page load, plus GET calls made by a modal or a page interaction.
PAGE_LOAD_ENDPOINTS = {
    "/": (
        "/dashboard/summary",
        "/dashboard/sales?year=2026",
        "/dashboard/purchases?year=2026",
        "/dashboard/top-products?limit=5",
        "/dashboard/low-stock?threshold=100",
        "/dashboard/payment-summary",
    ),
    "/products": ("/products/", "/categories/"),
    "/customers": ("/customers/",),
    "/suppliers": ("/suppliers/",),
    "/purchases": ("/purchases/", "/suppliers/", "/products/", "/purchases/1"),
    "/orders": ("/orders/", "/customers/", "/products/"),
    "/invoices": ("/invoices/", "/orders/", "/orders/1"),
    "/invoices/:invoiceId": ("/invoices/1",),
    "/deliveries": ("/deliveries/", "/invoices/"),
    "/payments": ("/payments/", "/invoices/"),
    "/purchase-payments": ("/purchase-payments/", "/purchases/"),
    "/returns": ("/returns/", "/invoices/", "/invoices/1"),
    "/inventory": ("/products/", "/inventory/stock/1"),
    "/users": ("/users",),
}

EXPECTED_SIDEBAR_PATHS = {
    "ADMIN": set(SIDEBAR_PAGE_PERMISSIONS),
    "SALES": {
        "/",
        "/products",
        "/customers",
        "/suppliers",
        "/orders",
        "/invoices",
        "/deliveries",
        "/payments",
        "/returns",
        "/inventory",
    },
    "WAREHOUSE": {
        "/",
        "/products",
        "/customers",
        "/suppliers",
        "/purchases",
        "/orders",
        "/invoices",
        "/deliveries",
        "/returns",
        "/inventory",
    },
    "ACCOUNTS": set(SIDEBAR_PAGE_PERMISSIONS) - {"/users"},
    "VIEWER": set(SIDEBAR_PAGE_PERMISSIONS) - {"/users"},
}


class FakeResult:
    def __init__(self, value=None):
        self.value = value

    def unique(self):
        return self

    def scalars(self):
        return self

    def mappings(self):
        return self

    def all(self):
        return []

    def scalar(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value

    def first(self):
        return self.value


class FakeSession:
    def __init__(self, user: User):
        self.user = user

    def execute(self, statement, *args, **kwargs):
        entities = getattr(statement, "column_descriptions", [])
        is_user_query = any(entity.get("entity") is User for entity in entities)
        if not is_user_query:
            return FakeResult()

        username = next(iter(statement.compile().params.values()), None)
        user = self.user if username and username.lower() == self.user.username.lower() else None
        return FakeResult(user)

    def get(self, model, user_id: int):
        if model is User and user_id == self.user.user_id:
            return self.user
        return None

    def scalar(self, statement):
        return 0

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def sidebar_permissions_from_layout():
    layout_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "Layout.jsx"
    layout_source = layout_path.read_text(encoding="utf-8")
    matches = re.findall(
        r'\{ to: "([^"]+)".*?requiredPermissions: \[([^\]]*)\] \}',
        layout_source,
    )
    return {
        path: frozenset(re.findall(r'"([^"]+)"', required_permissions))
        for path, required_permissions in matches
    }


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.user = User(
            user_id=1,
            username="Admin",
            full_name="Active Administrator",
            password_hash=hash_password("current-password"),
            role="ADMIN",
            status=USER_STATUSES[0],
        )
        self.db = FakeSession(self.user)

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def _headers_for(self, role: str):
        self.user.role = role
        return {"Authorization": f"Bearer {create_access_token(self.user.user_id)}"}

    def _request_as(self, role: str, method: str, path: str, **kwargs):
        return self.client.request(method, path, headers=self._headers_for(role), **kwargs)

    def test_admin_has_every_defined_permission(self):
        self.assertEqual(set(ROLE_PERMISSIONS), set(ROLES))
        self.assertEqual(ROLE_PERMISSIONS["ADMIN"], ALL_PERMISSIONS)

    def test_role_matrix_rejects_disallowed_actions(self):
        cases = (
            ("VIEWER", "POST", "/orders/"),
            ("SALES", "POST", "/purchases/"),
            ("SALES", "POST", "/purchase-payments/"),
            ("WAREHOUSE", "PATCH", "/returns/1/approve"),
            ("ACCOUNTS", "PATCH", "/returns/1/receive"),
        )

        for role, method, path in cases:
            with self.subTest(role=role, method=method, path=path):
                response = self._request_as(role, method, path, json={})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"detail": "You don't have permission to do this."})

    def test_accounts_can_approve_a_return(self):
        response = self._request_as("ACCOUNTS", "PATCH", "/returns/1/approve")

        self.assertNotEqual(response.status_code, 403)

    def test_sidebar_mapping_matches_the_frontend_and_expected_role_visibility(self):
        self.assertEqual(sidebar_permissions_from_layout(), SIDEBAR_PAGE_PERMISSIONS)

        for role in ROLES:
            with self.subTest(role=role):
                visible_paths = {
                    path
                    for path, required_permissions in SIDEBAR_PAGE_PERMISSIONS.items()
                    if required_permissions <= set(permissions_for_role(role))
                }
                self.assertEqual(visible_paths, EXPECTED_SIDEBAR_PATHS[role])

    def test_every_visible_sidebar_page_loads_without_a_forbidden_response(self):
        for role in ROLES:
            allowed_permissions = set(permissions_for_role(role))
            for page, required_permissions in SIDEBAR_PAGE_PERMISSIONS.items():
                if not required_permissions <= allowed_permissions:
                    continue

                for endpoint in PAGE_LOAD_ENDPOINTS[page]:
                    with self.subTest(role=role, page=page, endpoint=endpoint):
                        response = self._request_as(role, "GET", endpoint)
                        self.assertNotEqual(response.status_code, 403)

    def test_invoice_detail_loads_without_a_forbidden_response_for_every_invoice_reader(self):
        for role in ROLES:
            if "invoices:read" not in permissions_for_role(role):
                continue

            with self.subTest(role=role):
                response = self._request_as(role, "GET", "/invoices/1")
                self.assertNotEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
