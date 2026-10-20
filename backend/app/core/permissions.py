from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.core.auth import get_current_user
from app.core.roles import ROLES
from app.models.user import User


ADMIN, SALES, WAREHOUSE, ACCOUNTS, VIEWER = ROLES

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

ROLE_PERMISSIONS = {
    ADMIN: ALL_PERMISSIONS,
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
        }
    ),
    VIEWER: frozenset({f"{resource}:read" for resource in _READ_RESOURCES}),
}

# These authenticated endpoints intentionally need no business permission.
ANY_LOGGED_IN = frozenset(
    {
        ("GET", "/auth/me"),
        ("POST", "/auth/change-password"),
    }
)


def permissions_for_role(role: str) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(role, ()))


def require_permission(permission: str) -> Callable:
    if permission not in ALL_PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    def permission_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if permission not in ROLE_PERMISSIONS.get(current_user.role, ()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to do this.",
            )
        return current_user

    permission_dependency.required_permission = permission
    return permission_dependency
