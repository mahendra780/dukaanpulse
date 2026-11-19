from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import constant_time_matches, hash_csrf_token, hash_session_token
from app.core.roles import USER_STATUSES
from app.db.database import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership


@dataclass(frozen=True)
class AuthPrincipal:
    user: User
    session: AuthSession
    membership: WorkspaceMembership

    @property
    def workspace_id(self) -> int:
        return self.session.workspace_id


def _authentication_error(detail: str = "Authentication is required. Please sign in.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_current_principal(
    session_token: str | None = Cookie(default=None, alias=settings.COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    if not session_token:
        raise _authentication_error()

    session = db.execute(
        select(AuthSession).where(
            AuthSession.token_hash == hash_session_token(session_token)
        )
    ).scalar_one_or_none()

    if session is None:
        raise _authentication_error(
            "Your session is invalid. Please sign in again."
        )

    now = _now()

    idle_expired = (
        _as_utc(session.last_seen_at)
        + timedelta(minutes=settings.SESSION_IDLE_MINUTES)
        <= now
    )

    if (
        session.revoked_at is not None
        or _as_utc(session.expires_at) <= now
        or idle_expired
    ):
        if session.revoked_at is None:
            session.revoked_at = now
            db.commit()

        raise _authentication_error(
            "Your session has expired. Please sign in again."
        )

    # A valid session must always belong to a workspace.
    if session.workspace_id is None:
        session.revoked_at = now
        db.commit()
        raise _authentication_error(
            "Your session has no active workspace. Please sign in again."
        )

    user = db.get(User, session.user_id)

    if user is None or user.status != USER_STATUSES[0]:
        session.revoked_at = now
        db.commit()
        raise _authentication_error(
            "Your session is no longer active. Please sign in again."
        )

    # Validate both membership and workspace status.
    membership = db.execute(
        select(WorkspaceMembership)
        .join(
            Workspace,
            Workspace.workspace_id == WorkspaceMembership.workspace_id,
        )
        .where(
            WorkspaceMembership.workspace_id == session.workspace_id,
            WorkspaceMembership.user_id == user.user_id,
            WorkspaceMembership.status == "ACTIVE",
            Workspace.status == "ACTIVE",
        )
    ).scalar_one_or_none()

    if membership is None:
        session.revoked_at = now
        db.commit()
        raise _authentication_error(
            "Your workspace access is no longer active. Please sign in again."
        )

    if now - _as_utc(session.last_seen_at) >= timedelta(seconds=60):
        session.last_seen_at = now
        db.commit()

    return AuthPrincipal(
        user=user,
        session=session,
        membership=membership,
    )


def get_current_user(principal: AuthPrincipal = Depends(get_current_principal)) -> User:
    return principal.user


def require_workspace(
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> AuthPrincipal:
    db.info["workspace_id"] = principal.workspace_id
    return principal


def require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin:
        if origin not in settings.cors_allowed_origins:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request origin is not allowed.")
    elif settings.ENVIRONMENT == "production":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A trusted request origin is required.")


def csrf_protect(
    request: Request,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    principal: AuthPrincipal = Depends(get_current_principal),
) -> AuthPrincipal:
    if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return principal
    require_trusted_origin(request)
    if not csrf_token or not constant_time_matches(
        principal.session.csrf_token_hash, hash_csrf_token(csrf_token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your security token is missing or invalid.")
    return principal
