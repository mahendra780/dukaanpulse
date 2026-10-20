import os
import re
import unittest

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core.permissions import ANY_LOGGED_IN
from app.core.roles import USER_STATUSES
from app.core.security import create_access_token, hash_password
from app.db.database import get_db
from app.main import app
from app.models.user import User


PUBLIC_ROUTES = frozenset(
    {
        ("GET", "/"),
        ("GET", "/health"),
        ("POST", "/auth/login"),
        ("GET", "/docs"),
        ("HEAD", "/docs"),
        ("GET", "/docs/oauth2-redirect"),
        ("HEAD", "/docs/oauth2-redirect"),
        ("GET", "/redoc"),
        ("HEAD", "/redoc"),
        ("GET", "/openapi.json"),
        ("HEAD", "/openapi.json"),
    }
)

ROUTER_PROBES = {
    "Categories": ("GET", "/categories/", {}, 200),
    "Products": ("POST", "/products/", {"json": {}}, 422),
    "Customers": ("POST", "/customers/", {"json": {}}, 422),
    "Suppliers": ("POST", "/suppliers/", {"json": {}}, 422),
    "Purchases": ("POST", "/purchases/", {"json": {}}, 422),
    "Inventory": ("GET", "/inventory/stock/not-a-number", {}, 422),
    "Orders": ("POST", "/orders/", {"json": {}}, 422),
    "Invoices": ("POST", "/invoices/", {"json": {}}, 422),
    "Deliveries": ("POST", "/deliveries/", {"json": {}}, 422),
    "Payments": ("POST", "/payments/", {"json": {}}, 422),
    "Purchase Payments": ("POST", "/purchase-payments/", {"json": {}}, 422),
    "Returns": ("POST", "/returns/", {"json": {}}, 422),
    "Users": ("GET", "/users", {}, 200),
    "Dashboard": ("GET", "/dashboard/sales?year=not-a-year", {}, 422),
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


class FakeSession:
    def __init__(self, user: User):
        self.user = user

    def execute(self, statement):
        entities = getattr(statement, "column_descriptions", [])
        is_user_query = any(
            entity.get("entity") is User for entity in entities
        )
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


def concrete_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


def concrete_routes(routes=app.routes):
    for route in routes:
        included_router = getattr(route, "original_router", None)
        if included_router is not None:
            yield from concrete_routes(included_router.routes)
        elif hasattr(route, "methods") and hasattr(route, "path"):
            yield route


def route_keys():
    for route in concrete_routes():
        for method in route.methods or set():
            if method != "OPTIONS":
                yield method, route.path


def route_permissions(route):
    return {
        dependency.dependency.required_permission
        for dependency in route.dependencies
        if hasattr(dependency.dependency, "required_permission")
    }


class RouteAuthenticationAuditTests(unittest.TestCase):
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

    def _authorization_headers(self):
        return {"Authorization": f"Bearer {create_access_token(self.user.user_id)}"}

    def test_every_non_public_route_requires_login(self):
        protected_routes = sorted(set(route_keys()) - PUBLIC_ROUTES)

        self.assertTrue(protected_routes)
        for method, path in protected_routes:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, concrete_path(path))

                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")

    def test_every_non_public_route_has_one_permission_or_is_explicitly_logged_in_only(self):
        routes_by_key = {
            (method, route.path): route
            for route in concrete_routes()
            for method in route.methods or set()
            if method != "OPTIONS"
        }
        protected_routes = set(routes_by_key) - PUBLIC_ROUTES

        self.assertTrue(ANY_LOGGED_IN <= protected_routes)
        for route_key in sorted(protected_routes):
            with self.subTest(method=route_key[0], path=route_key[1]):
                if route_key in ANY_LOGGED_IN:
                    self.assertEqual(route_permissions(routes_by_key[route_key]), set())
                else:
                    self.assertEqual(
                        len(route_permissions(routes_by_key[route_key])),
                        1,
                    )

    def test_every_public_route_is_reachable_without_a_token(self):
        discovered_routes = set(route_keys())
        self.assertTrue(PUBLIC_ROUTES <= discovered_routes)

        for method, path in sorted(PUBLIC_ROUTES):
            with self.subTest(method=method, path=path):
                request_options = {}
                if (method, path) == ("POST", "/auth/login"):
                    request_options["data"] = {
                        "username": "Admin",
                        "password": "current-password",
                    }

                response = self.client.request(method, path, **request_options)
                self.assertEqual(response.status_code, 200)

    def test_cors_preflight_with_authorization_is_not_rejected(self):
        response = self.client.options(
            "/products/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization",
            },
        )

        self.assertNotEqual(response.status_code, 401)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"],
            "http://localhost:5173",
        )
        self.assertIn(
            "authorization",
            response.headers["Access-Control-Allow-Headers"].lower(),
        )

    def test_valid_token_reaches_each_business_router(self):
        protected_router_tags = {
            tag
            for route in concrete_routes()
            if isinstance(route, APIRoute) and route.tags != ["Authentication"]
            for tag in route.tags
        }
        self.assertEqual(set(ROUTER_PROBES), protected_router_tags)

        for router_name, (method, path, request_options, expected_status) in ROUTER_PROBES.items():
            with self.subTest(router=router_name):
                response = self.client.request(
                    method,
                    path,
                    headers=self._authorization_headers(),
                    **request_options,
                )

                self.assertEqual(response.status_code, expected_status)


if __name__ == "__main__":
    unittest.main()
