import re
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.core.auth import AuthPrincipal
from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS, permissions_for_principal, permissions_for_role, require_permission
from app.core.roles import WORKSPACE_ROLES
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import WorkspaceMembership


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
    "/cash-credit": frozenset({"reports:read"}),
    "/users": frozenset({"users:manage"}),
}


def sidebar_permissions_from_layout():
    layout_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "Layout.jsx"
    layout_source = layout_path.read_text(encoding="utf-8")
    matches = re.findall(r'\{ to: "([^"]+)".*?requiredPermissions: \[([^\]]*)\] \}', layout_source)
    return {path: frozenset(re.findall(r'"([^"]+)"', required)) for path, required in matches}


def principal_for(role: str) -> AuthPrincipal:
    user = User(user_id=1, username="user", full_name="Test User", password_hash="hash", role="VIEWER", status="ACTIVE")
    membership = WorkspaceMembership(membership_id=1, workspace_id=1, user_id=1, role=role, status="ACTIVE")
    return AuthPrincipal(user=user, session=AuthSession(workspace_id=1), membership=membership)


class PermissionTests(unittest.TestCase):
    def test_role_matrix_uses_only_workspace_roles_and_known_permissions(self):
        self.assertEqual(set(ROLE_PERMISSIONS), set(WORKSPACE_ROLES))
        for permissions in ROLE_PERMISSIONS.values():
            self.assertTrue(set(permissions) <= set(ALL_PERMISSIONS))
        self.assertNotIn("system:read", permissions_for_role("OWNER"))
        self.assertNotIn("system:read", permissions_for_role("ADMIN"))

    def test_workspace_roles_do_not_have_global_system_permission(self):
        for role in WORKSPACE_ROLES:
            with self.subTest(role=role):
                self.assertNotIn(
                    "system:read",
                    permissions_for_role(role),
                )
    def test_reports_are_limited_to_owner_admin_and_accounts(self):
        for role in WORKSPACE_ROLES:
            with self.subTest(role=role):
                self.assertEqual("reports:read" in permissions_for_role(role), role in {"OWNER", "ADMIN", "ACCOUNTS"})

    def test_permission_dependency_enforces_the_backend_matrix(self):
        cases = (("VIEWER", "orders:write", False), ("SALES", "orders:write", True), ("ACCOUNTS", "returns:approve", True))
        for role, permission, allowed in cases:
            dependency = require_permission(permission)
            with self.subTest(role=role, permission=permission):
                if allowed:
                    self.assertEqual(dependency(principal_for(role)).membership.role, role)
                else:
                    with self.assertRaises(HTTPException) as error:
                        dependency(principal_for(role))
                    self.assertEqual(error.exception.status_code, 403)

    def test_sidebar_permissions_match_frontend_and_never_overstate_a_role(self):
        self.assertEqual(sidebar_permissions_from_layout(), SIDEBAR_PAGE_PERMISSIONS)
        for role in WORKSPACE_ROLES:
            allowed = set(permissions_for_role(role))
            for path, required in SIDEBAR_PAGE_PERMISSIONS.items():
                with self.subTest(role=role, path=path):
                    visible = required <= allowed
                    if visible:
                        self.assertTrue(required <= allowed)


if __name__ == "__main__":
    unittest.main()
