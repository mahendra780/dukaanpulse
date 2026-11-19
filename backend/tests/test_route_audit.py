import os
import re
import unittest

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.core.permissions import ANY_LOGGED_IN
from app.main import app


PUBLIC_ROUTES = frozenset(
    {
        ("GET", "/"), ("GET", "/health"),
        ("POST", "/auth/signup"), ("POST", "/auth/signup/resend-otp"),
        ("POST", "/auth/signup/verify-otp"), ("POST", "/auth/otp/resend"),
        ("POST", "/auth/login"), ("POST", "/auth/forgot-password"),
        ("POST", "/auth/reset-password/verify-otp"), ("POST", "/auth/reset-password"),
        ("POST", "/business/invitations/accept"), ("POST", "/business/invitations/verify-otp"),
        ("GET", "/docs"), ("HEAD", "/docs"),
        ("GET", "/docs/oauth2-redirect"), ("HEAD", "/docs/oauth2-redirect"),
        ("GET", "/redoc"), ("HEAD", "/redoc"),
        ("GET", "/openapi.json"), ("HEAD", "/openapi.json"),
    }
)


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


def concrete_path(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


def _dependency_calls(dependency):
    call = getattr(dependency, "call", getattr(dependency, "dependency", None))
    if call is not None:
        yield call
    for child in getattr(dependency, "dependencies", ()):
        yield from _dependency_calls(child)


def route_permissions(route: APIRoute) -> set[str]:
    calls = []
    for dependency in route.dependencies:
        calls.extend(_dependency_calls(dependency))
    calls.extend(_dependency_calls(route.dependant))
    return {call.required_permission for call in calls if hasattr(call, "required_permission")}


class RouteAuthenticationAuditTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()

    def test_every_non_public_route_requires_a_cookie_session(self):
        protected_routes = sorted(set(route_keys()) - PUBLIC_ROUTES)
        self.assertTrue(protected_routes)
        for method, path in protected_routes:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, concrete_path(path))
                self.assertEqual(response.status_code, 401)

    def test_every_non_public_route_has_a_permission_or_is_explicitly_session_only(self):
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
                    self.assertEqual(len(route_permissions(routes_by_key[route_key])), 1)

    def test_public_route_table_is_explicit_and_cors_allows_the_configured_frontend(self):
        discovered = set(route_keys())
        self.assertTrue(PUBLIC_ROUTES <= discovered)
        response = self.client.options(
            "/products/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, X-CSRF-Token",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        self.assertIn("x-csrf-token", response.headers["Access-Control-Allow-Headers"].lower())


if __name__ == "__main__":
    unittest.main()
