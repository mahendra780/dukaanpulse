from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, Response, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    constant_time_matches,
    generate_otp,
    generate_secret,
    hash_csrf_token,
    hash_otp,
    hash_reset_or_invitation_token,
    hash_session_token,
)
from app.models.auth_lifecycle import (
    AuthRateLimitEvent,
    OtpChallenge,
    PasswordResetGrant,
    SecurityAuditEvent,
    WorkspaceInvitation,
)
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.services.sms_provider import SmsDeliveryError, SmsProvider


OTP_PURPOSES = ("SIGNUP", "PASSWORD_RESET", "INVITATION")
OTP_EXPIRY_MINUTES = 5
OTP_RESEND_SECONDS = 30
OTP_MAX_ATTEMPTS = 5


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    """Normalise driver-returned timestamps before security comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _hashed_rate_limit_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def enforce_rate_limit(
    db: Session,
    *,
    scope: str,
    value: str,
    event_type: str,
    limit: int,
    window: timedelta,
    now: datetime | None = None,
) -> None:
    """Persist an auditable, privacy-preserving rate-limit event.

    The migration indexes scope/key/event/time. PostgreSQL advisory locking is
    deliberately omitted here so the service remains database-neutral in test
    doubles; the unique state transitions on OTP/session objects provide the
    stronger account-level concurrency boundary.
    """
    now = now or utc_now()
    key_hash = _hashed_rate_limit_key(value)
    count = db.scalar(
        select(func.count(AuthRateLimitEvent.rate_limit_event_id)).where(
            AuthRateLimitEvent.scope == scope,
            AuthRateLimitEvent.key_hash == key_hash,
            AuthRateLimitEvent.event_type == event_type,
            AuthRateLimitEvent.created_at >= now - window,
        )
    )
    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait before trying again.",
        )
    db.add(AuthRateLimitEvent(scope=scope, key_hash=key_hash, event_type=event_type))


def write_audit_event(
    db: Session,
    event_type: str,
    *,
    user_id: int | None = None,
    workspace_id: int | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        SecurityAuditEvent(
            event_type=event_type,
            user_id=user_id,
            workspace_id=workspace_id,
            detail=detail,
        )
    )


def _invitation_workspace_id(
    db: Session,
    invitation_id: int | None,
) -> int | None:
    if invitation_id is None:
        return None

    invitation = db.get(WorkspaceInvitation, invitation_id)
    return invitation.workspace_id if invitation is not None else None


def start_otp_challenge(
    db: Session,
    provider: SmsProvider,
    *,
    purpose: Literal["SIGNUP", "PASSWORD_RESET", "INVITATION"],
    mobile_e164: str,
    user_id: int | None = None,
    invitation_id: int | None = None,
    pending_username: str | None = None,
    pending_full_name: str | None = None,
    pending_business_name: str | None = None,
    pending_password_hash: str | None = None,
    client_ip: str,
    now: datetime | None = None,
) -> OtpChallenge:
    now = now or utc_now()
    enforce_rate_limit(
        db, scope="mobile", value=mobile_e164, event_type="otp_send", limit=5, window=timedelta(hours=1), now=now
    )
    enforce_rate_limit(
        db, scope="ip", value=client_ip, event_type="otp_send", limit=10, window=timedelta(hours=1), now=now
    )
    enforce_rate_limit(
        db, scope="global", value="otp", event_type="otp_send", limit=500, window=timedelta(hours=1), now=now
    )
    public_id = uuid4()
    code = generate_otp()
    challenge = OtpChallenge(
        public_id=public_id,
        purpose=purpose,
        mobile_e164=mobile_e164,
        otp_hash=hash_otp(str(public_id), code),
        user_id=user_id,
        invitation_id=invitation_id,
        pending_username=pending_username,
        pending_full_name=pending_full_name,
        pending_business_name=pending_business_name,
        pending_password_hash=pending_password_hash,
        attempts=0,
        sent_at=now,
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )
    db.add(challenge)
    try:
        provider.send_otp(mobile_e164, code, purpose)
    except SmsDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is unavailable right now. Please try again later.",
        ) from exc
    write_audit_event(db, "otp_requested", user_id=user_id,workspace_id=_invitation_workspace_id(db, invitation_id), detail=purpose)
    return challenge


def resend_otp_challenge(
    db: Session,
    provider: SmsProvider,
    *,
    public_id: UUID,
    client_ip: str,
    expected_purpose: str | None = None,
    now: datetime | None = None,
) -> OtpChallenge:
    now = now or utc_now()
    challenge = db.execute(
        select(OtpChallenge).where(OtpChallenge.public_id == public_id).with_for_update()
    ).scalar_one_or_none()
    if (
        challenge is None
        or challenge.consumed_at is not None
        or as_utc(challenge.expires_at) <= now
        or (expected_purpose is not None and challenge.purpose != expected_purpose)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This verification request is no longer valid.")
    if as_utc(challenge.sent_at) + timedelta(seconds=OTP_RESEND_SECONDS) > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Please wait before requesting another code.")
    enforce_rate_limit(
        db, scope="mobile", value=challenge.mobile_e164, event_type="otp_send", limit=5, window=timedelta(hours=1), now=now
    )
    enforce_rate_limit(
        db, scope="ip", value=client_ip, event_type="otp_send", limit=10, window=timedelta(hours=1), now=now
    )
    enforce_rate_limit(
        db, scope="global", value="otp", event_type="otp_send", limit=500, window=timedelta(hours=1), now=now
    )
    code = generate_otp()
    challenge.otp_hash = hash_otp(str(challenge.public_id), code)
    challenge.attempts = 0
    challenge.sent_at = now
    challenge.expires_at = now + timedelta(minutes=OTP_EXPIRY_MINUTES)
    try:
        provider.send_otp(challenge.mobile_e164, code, challenge.purpose)
    except SmsDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is unavailable right now. Please try again later.",
        ) from exc
    write_audit_event(db, "otp_resent", user_id=challenge.user_id,workspace_id=_invitation_workspace_id(db, challenge.invitation_id), detail=challenge.purpose)
    return challenge


def verify_otp_challenge(
    db: Session,
    *,
    public_id: UUID,
    code: str,
    purpose: str,
    client_ip: str,
    now: datetime | None = None,
) -> OtpChallenge:
    now = now or utc_now()
    enforce_rate_limit(
        db, scope="ip", value=client_ip, event_type="otp_verify", limit=30, window=timedelta(minutes=15), now=now
    )
    challenge = db.execute(
        select(OtpChallenge).where(OtpChallenge.public_id == public_id).with_for_update()
    ).scalar_one_or_none()
    if (
        challenge is None
        or challenge.purpose != purpose
        or challenge.consumed_at is not None
        or as_utc(challenge.expires_at) <= now
        or challenge.attempts >= OTP_MAX_ATTEMPTS
    ):
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The verification code is invalid or expired.")
    enforce_rate_limit(
        db, scope="mobile", value=challenge.mobile_e164, event_type="otp_verify", limit=10, window=timedelta(minutes=15), now=now
    )
    enforce_rate_limit(
        db, scope="global", value="otp", event_type="otp_verify", limit=1_000, window=timedelta(minutes=15), now=now
    )
    workspace_id = _invitation_workspace_id(db, challenge.invitation_id)
    if not constant_time_matches(challenge.otp_hash, hash_otp(str(challenge.public_id), code)):
        challenge.attempts += 1

        write_audit_event(
            db,
            "otp_failed",
            user_id=challenge.user_id,
            workspace_id=workspace_id,
            detail=purpose,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The verification code is invalid or expired.")
    challenge.consumed_at = now
    write_audit_event(db, "otp_verified", user_id=challenge.user_id,workspace_id=workspace_id, detail=purpose)
    return challenge


def issue_session(
    db: Session,
    *,
    user_id: int,
    workspace_id: int,
    now: datetime | None = None,
) -> tuple[AuthSession, str, str]:
    now = now or utc_now()

    user = db.execute(
        select(User).where(
            User.user_id == user_id,
            User.status == "ACTIVE",
        )
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active user account is required.",
        )

    membership = db.execute(
        select(WorkspaceMembership)
        .join(
            Workspace,
            Workspace.workspace_id == WorkspaceMembership.workspace_id,
        )
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.status == "ACTIVE",
            Workspace.status == "ACTIVE",
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="An active workspace membership is required.",
        )

    token = generate_secret()
    csrf_token = generate_secret()

    session = AuthSession(
        user_id=user_id,
        workspace_id=workspace_id,
        token_hash=hash_session_token(token),
        csrf_token_hash=hash_csrf_token(csrf_token),
        last_seen_at=now,
        expires_at=now + timedelta(hours=settings.SESSION_ABSOLUTE_HOURS),
    )

    db.add(session)

    return session, token, csrf_token


def set_session_cookies(response: Response, *, session_token: str, csrf_token: str) -> None:
    attributes = {
        "max_age": settings.SESSION_ABSOLUTE_HOURS * 60 * 60,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        attributes["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(settings.COOKIE_NAME, session_token, httponly=True, **attributes)
    response.set_cookie(settings.CSRF_COOKIE_NAME, csrf_token, httponly=False, **attributes)


def clear_session_cookies(response: Response) -> None:
    attributes = {"path": "/", "secure": settings.cookie_secure, "samesite": "lax"}
    if settings.COOKIE_DOMAIN:
        attributes["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(settings.COOKIE_NAME, **attributes)
    response.delete_cookie(settings.CSRF_COOKIE_NAME, **attributes)


def revoke_user_sessions(db: Session, user_id: int, *, now: datetime | None = None) -> None:
    db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now or utc_now())
    )


def create_reset_grant(db: Session, user_id: int, *, now: datetime | None = None) -> str:
    now = now or utc_now()
    raw_token = generate_secret()
    db.add(
        PasswordResetGrant(
            user_id=user_id,
            token_hash=hash_reset_or_invitation_token(raw_token),
            expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_GRANT_MINUTES),
        )
    )
    return raw_token
