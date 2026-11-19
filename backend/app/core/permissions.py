from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.auth import AuthPrincipal, get_current_principal
from app.core.roles import ROLES, WORKSPACE_ROLES


ADMIN, SALES, WAREHOUSE, ACCOUNTS, VIEWER = ROLES
OWNER = WORKSPACE_ROLES[0]

_READ_RESOURCES = frozenset(
    {
        "categories",
        "products",
        "customers",
        "suppliers",
        "purchases",
        "orders",
        "invoices",
        "deliveries",
        "payments",
        "purchase_payments",
        "returns",
        "inventory",
        "dashboard",
        "reports",
    }
)
_WRITE_RESOURCES = frozenset(
    {
        "categories",
        "products",
        "customers",
        "suppliers",
        "purchases",
        "orders",
        "invoices",
        "deliveries",
        "payments",
        "purchase_payments",
        "returns",
    }
)

ALL_PERMISSIONS = frozenset(
    {f"{resource}:read" for resource in _READ_RESOURCES}
    | {f"{resource}:write" for resource in _WRITE_RESOURCES}
    | {"returns:approve", "returns:receive", "system:read", "users:manage"}
)

_WORKSPACE_ADMIN_PERMISSIONS = ALL_PERMISSIONS - {"system:read"}

ROLE_PERMISSIONS = {
    OWNER: _WORKSPACE_ADMIN_PERMISSIONS,
    ADMIN: _WORKSPACE_ADMIN_PERMISSIONS,
    SALES: frozenset(
        {
            "categories:read",
            "products:read",
            "customers:read",
            "customers:write",
            "suppliers:read",
            "orders:read",
            "orders:write",
            "invoices:read",
            "invoices:write",
            "deliveries:read",
            "payments:read",
            "payments:write",
            "returns:read",
            "returns:write",
            "inventory:read",
            "dashboard:read",
        }
    ),
    WAREHOUSE: frozenset(
        {
            "categories:read",
            "categories:write",
            "products:read",
            "products:write",
            "suppliers:read",
            "suppliers:write",
            "customers:read",
            "purchases:read",
            "purchases:write",
            "orders:read",
            "invoices:read",
            "deliveries:read",
            "deliveries:write",
            "returns:read",
            "returns:receive",
            "inventory:read",
            "dashboard:read",
        }
    ),
    ACCOUNTS: frozenset(
        {
            "categories:read",
            "products:read",
            "customers:read",
            "suppliers:read",
            "purchases:read",
            "orders:read",
            "invoices:read",
            "deliveries:read",
            "payments:read",
            "payments:write",
            "purchase_payments:read",
            "purchase_payments:write",
            "returns:read",
            "returns:approve",
            "inventory:read",
            "dashboard:read",
            "reports:read",
        }
    ),
    VIEWER: frozenset(
        f"{resource}:read" for resource in _READ_RESOURCES - {"reports"}
    ),
}

# These authenticated endpoints intentionally need no business permission.
ANY_LOGGED_IN = frozenset(
    {
        ("GET", "/auth/me"),
        ("POST", "/auth/logout"),
        ("POST", "/auth/switch-workspace"),
        ("POST", "/auth/change-password"),
        ("GET", "/auth/sessions"),
        ("DELETE", "/auth/sessions/{session_id}"),
    }
)


def permissions_for_role(role: str) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(role, ()))


def permissions_for_principal(principal: AuthPrincipal) -> list[str]:
    return permissions_for_role(principal.membership.role)


def require_permission(permission: str) -> Callable:
    if permission not in ALL_PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    def permission_dependency(
        principal: AuthPrincipal = Depends(get_current_principal),
    ) -> AuthPrincipal:
        if permission not in permissions_for_principal(principal):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to do this.",
            )
        return principal

    permission_dependency.required_permission = permission
    return permission_dependency
