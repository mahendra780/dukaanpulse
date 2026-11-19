from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import (
    AuthPrincipal,
    csrf_protect,
    get_current_principal,
    require_trusted_origin,
)
from app.core.config import settings
from app.core.mobile import normalize_mobile
from app.core.permissions import permissions_for_principal
from app.core.roles import USER_STATUSES
from app.core.security import (
    hash_password,
    hash_reset_or_invitation_token,
    verify_password,
    verify_password_against_dummy,
)
from app.db.database import get_db
from app.models.auth_lifecycle import OtpChallenge, PasswordResetGrant, SecurityAuditEvent
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.auth import (
    ChangePasswordRequest,
    ChallengeResponse,
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OtpResendRequest,
    OtpVerifyRequest,
    ResetGrantResponse,
    ResetPasswordRequest,
    RecoveryChallengeResponse,
    SessionResponse,
    SignupRequest,
    SwitchWorkspaceRequest,
    WorkspaceSummary,
)
from app.services.auth_lifecycle import (
    OTP_MAX_ATTEMPTS,
    clear_session_cookies,
    create_reset_grant,
    enforce_rate_limit,
    issue_session,
    resend_otp_challenge,
    as_utc,
    revoke_user_sessions,
    set_session_cookies,
    start_otp_challenge,
    utc_now,
    verify_otp_challenge,
    write_audit_event,
)
from app.services.sms_provider import SmsProvider, get_sms_provider


router = APIRouter(prefix="/auth", tags=["Authentication"])

_INVALID_CREDENTIALS_DETAIL = "Incorrect username, mobile number, or password."
_GENERIC_RECOVERY_DETAIL = "If that mobile number is eligible, a verification code has been sent."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _validate_password(password: str, confirmation: str) -> None:
    if password != confirmation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match.")
    if len(password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters long.",
        )


def _validate_username(username: str) -> str:
    username = username.strip()
    if not username or len(username) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username must be between 1 and 50 characters.")
    return username


def _validate_name(value: str, label: str, maximum: int) -> str:
    value = value.strip()
    if not value or len(value) > maximum:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} must be between 1 and {maximum} characters.")
    return value


def _current_workspace_summary(db: Session, principal: AuthPrincipal) -> WorkspaceSummary | None:
    if principal.workspace_id is None:
        return None
    workspace = db.get(Workspace, principal.workspace_id)
    if workspace is None:
        return None
    return WorkspaceSummary(
        workspace_id=workspace.workspace_id,
        business_name=workspace.business_name,
        role=principal.membership.role,
    )


def _membership_summaries(db: Session, user_id: int) -> list[WorkspaceSummary]:
    rows = db.execute(
        select(WorkspaceMembership, Workspace)
        .join(Workspace, Workspace.workspace_id == WorkspaceMembership.workspace_id)
        .where(
            WorkspaceMembership.user_id == user_id,
            WorkspaceMembership.status == "ACTIVE",
            Workspace.status == "ACTIVE",
        )
        .order_by(WorkspaceMembership.created_at)
    ).all()
    return [
        WorkspaceSummary(workspace_id=workspace.workspace_id, business_name=workspace.business_name, role=membership.role)
        for membership, workspace in rows
    ]


@router.post("/signup", response_model=ChallengeResponse, status_code=status.HTTP_202_ACCEPTED)
def signup(
    data: SignupRequest,
    request: Request,
    db: Session = Depends(get_db),
    provider: SmsProvider = Depends(get_sms_provider),
):
    require_trusted_origin(request)
    full_name = _validate_name(data.full_name, "Full name", 100)
    business_name = _validate_name(data.business_name, "Business name", 150)
    username = _validate_username(data.username)
    _validate_password(data.password, data.confirm_password)
    mobile_e164 = normalize_mobile(data.mobile_number)
    existing = db.execute(
        select(User.user_id).where(
            or_(func.lower(User.username) == username.lower(), User.mobile_e164 == mobile_e164)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This username or mobile number cannot be used.")
    try:
        challenge = start_otp_challenge(
            db,
            provider,
            purpose="SIGNUP",
            mobile_e164=mobile_e164,
            pending_username=username,
            pending_full_name=full_name,
            pending_business_name=business_name,
            pending_password_hash=hash_password(data.password),
            client_ip=_client_ip(request),
        )
        db.commit()
        return ChallengeResponse(challenge_id=challenge.public_id)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This username or mobile number cannot be used.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to start verification right now. Please try again.") from exc


@router.post("/signup/resend-otp", response_model=ChallengeResponse, status_code=status.HTTP_202_ACCEPTED)
def resend_signup_otp(
    data: OtpResendRequest,
    request: Request,
    db: Session = Depends(get_db),
    provider: SmsProvider = Depends(get_sms_provider),
):
    require_trusted_origin(request)
    try:
        challenge = resend_otp_challenge(
            db, provider, public_id=data.challenge_id, client_ip=_client_ip(request), expected_purpose="SIGNUP"
        )
        db.commit()
        return ChallengeResponse(challenge_id=challenge.public_id)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to resend verification right now. Please try again.") from exc


@router.post("/otp/resend", response_model=ChallengeResponse, status_code=status.HTTP_202_ACCEPTED)
def resend_otp(
    data: OtpResendRequest,
    request: Request,
    db: Session = Depends(get_db),
    provider: SmsProvider = Depends(get_sms_provider),
):
    require_trusted_origin(request)
    try:
        challenge = resend_otp_challenge(db, provider, public_id=data.challenge_id, client_ip=_client_ip(request))
        db.commit()
        return ChallengeResponse(challenge_id=challenge.public_id)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to resend verification right now. Please try again.") from exc


@router.post("/signup/verify-otp", response_model=CurrentUserResponse)
def verify_signup_otp(
    data: OtpVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    require_trusted_origin(request)
    try:
        challenge = verify_otp_challenge(
            db, public_id=data.challenge_id, code=data.code, purpose="SIGNUP", client_ip=_client_ip(request)
        )
        if not all((challenge.pending_username, challenge.pending_full_name, challenge.pending_business_name, challenge.pending_password_hash)):
            raise HTTPException(status_code=400, detail="This verification request is no longer valid.")
        duplicate = db.execute(
            select(User.user_id).where(
                or_(
                    func.lower(User.username) == challenge.pending_username.lower(),
                    User.mobile_e164 == challenge.mobile_e164,
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="This username or mobile number cannot be used.")
        now = utc_now()
        user = User(
            username=challenge.pending_username,
            full_name=challenge.pending_full_name,
            password_hash=challenge.pending_password_hash,
            role="VIEWER",
            status="ACTIVE",
            mobile_e164=challenge.mobile_e164,
            mobile_verified_at=now,
        )
        workspace = Workspace(business_name=challenge.pending_business_name, status="ACTIVE")
        db.add_all((user, workspace))
        db.flush()
        membership = WorkspaceMembership(workspace_id=workspace.workspace_id, user_id=user.user_id, role="OWNER", status="ACTIVE")
        db.add(membership)
        db.flush()
        write_audit_event(db, "owner_signup_verified", user_id=user.user_id, workspace_id=workspace.workspace_id)
        _, session_token, csrf_token = issue_session(db, user_id=user.user_id, workspace_id=workspace.workspace_id, now=now)
        db.commit()
        set_session_cookies(response, session_token=session_token, csrf_token=csrf_token)
        return CurrentUserResponse(
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            mobile_e164=user.mobile_e164,
            workspace=WorkspaceSummary(workspace_id=workspace.workspace_id, business_name=workspace.business_name, role="OWNER"),
            memberships=[WorkspaceSummary(workspace_id=workspace.workspace_id, business_name=workspace.business_name, role="OWNER")],
            permissions=sorted(permissions_for_principal(AuthPrincipal(user=user, session=AuthSession(workspace_id=workspace.workspace_id), membership=membership))),
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This username or mobile number cannot be used.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to verify your account right now. Please try again.") from exc


@router.post("/login", response_model=CurrentUserResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    require_trusted_origin(request)
    identifier = data.identifier.strip()
    now = utc_now()
    try:
        enforce_rate_limit(
            db, scope="ip", value=_client_ip(request), event_type="login", limit=30, window=timedelta(minutes=15), now=now
        )
        mobile = None
        try:
            mobile = normalize_mobile(identifier)
        except HTTPException:
            pass
        predicates = [func.lower(User.username) == identifier.lower()]
        if mobile:
            predicates.append(User.mobile_e164 == mobile)
        user = db.execute(select(User).where(or_(*predicates)).with_for_update()).scalar_one_or_none()
        if user is None:
            verify_password_against_dummy(data.password)
            db.commit()
            raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS_DETAIL)
        if user.locked_until is not None and as_utc(user.locked_until) > now:
            verify_password_against_dummy(data.password)
            db.commit()
            raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS_DETAIL)
        if user.locked_until is not None and as_utc(user.locked_until) <= now:
            user.failed_login_count = 0
            user.locked_until = None
        if not verify_password(data.password, user.password_hash) or user.status != USER_STATUSES[0]:
            if user.status == USER_STATUSES[0]:
                user.failed_login_count = (user.failed_login_count or 0) + 1
                if user.failed_login_count >= settings.FAILED_LOGIN_ATTEMPT_THRESHOLD:
                    user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                    write_audit_event(db, "login_locked", user_id=user.user_id)
            write_audit_event(db, "login_failed", user_id=user.user_id)
            db.commit()
            raise HTTPException(status_code=401, detail=_INVALID_CREDENTIALS_DETAIL)
        membership = db.execute(
            select(WorkspaceMembership)
            .join(
                Workspace,
                Workspace.workspace_id == WorkspaceMembership.workspace_id,
            )
            .where(
                WorkspaceMembership.user_id == user.user_id,
                WorkspaceMembership.status == "ACTIVE",
                Workspace.status == "ACTIVE",
            )
            .order_by(WorkspaceMembership.created_at)
        ).scalars().first()

        if membership is None:
            verify_password_against_dummy(data.password)
            db.commit()
            raise HTTPException(
                status_code=401,
                detail=_INVALID_CREDENTIALS_DETAIL,
            )
        user.last_login_at = now
        user.failed_login_count = 0
        user.locked_until = None
        revoke_user_sessions(db, user.user_id, now=now)
        workspace_id = membership.workspace_id
        _, session_token, csrf_token = issue_session(db, user_id=user.user_id, workspace_id=workspace_id, now=now)
        write_audit_event(db, "login_succeeded", user_id=user.user_id, workspace_id=workspace_id)
        db.commit()
        set_session_cookies(response, session_token=session_token, csrf_token=csrf_token)
        principal = AuthPrincipal(user=user, session=AuthSession(workspace_id=workspace_id), membership=membership)
        return CurrentUserResponse(
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            mobile_e164=user.mobile_e164 if user.mobile_verified_at else None,
            workspace=_current_workspace_summary(db, principal),
            memberships=_membership_summaries(db, user.user_id),
            permissions=permissions_for_principal(principal),
        )
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to sign in right now. Please try again.") from exc


@router.post("/logout", response_model=MessageResponse, dependencies=[Depends(csrf_protect)])
def logout(
    response: Response,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    principal.session.revoked_at = utc_now()
    write_audit_event(db, "logout", user_id=principal.user.user_id, workspace_id=principal.workspace_id)
    db.commit()
    clear_session_cookies(response)
    return {"message": "Signed out successfully."}


@router.get("/me", response_model=CurrentUserResponse)
def get_me(principal: AuthPrincipal = Depends(get_current_principal), db: Session = Depends(get_db)):
    user = principal.user
    return CurrentUserResponse(
        user_id=user.user_id,
        username=user.username,
        full_name=user.full_name,
        mobile_e164=user.mobile_e164 if user.mobile_verified_at else None,
        workspace=_current_workspace_summary(db, principal),
        memberships=_membership_summaries(db, user.user_id),
        permissions=permissions_for_principal(principal),
    )


@router.post("/switch-workspace", response_model=CurrentUserResponse, dependencies=[Depends(csrf_protect)])
def switch_workspace(
    data: SwitchWorkspaceRequest,
    response: Response,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    membership = db.execute(
        select(WorkspaceMembership)
        .join(
            Workspace,
            Workspace.workspace_id == WorkspaceMembership.workspace_id,
        )
        .where(
            WorkspaceMembership.user_id == principal.user.user_id,
            WorkspaceMembership.workspace_id == data.workspace_id,
            WorkspaceMembership.status == "ACTIVE",
            Workspace.status == "ACTIVE",
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    principal.session.revoked_at = utc_now()
    _, token, csrf_token = issue_session(db, user_id=principal.user.user_id, workspace_id=membership.workspace_id)
    db.commit()
    set_session_cookies(response, session_token=token, csrf_token=csrf_token)
    switched = AuthPrincipal(user=principal.user, session=AuthSession(workspace_id=membership.workspace_id), membership=membership)
    return CurrentUserResponse(
        user_id=principal.user.user_id,
        username=principal.user.username,
        full_name=principal.user.full_name,
        mobile_e164=principal.user.mobile_e164 if principal.user.mobile_verified_at else None,
        workspace=_current_workspace_summary(db, switched),
        memberships=_membership_summaries(db, principal.user.user_id),
        permissions=permissions_for_principal(switched),
    )


@router.post("/change-password", response_model=MessageResponse, dependencies=[Depends(csrf_protect)])
def change_password(
    data: ChangePasswordRequest,
    response: Response,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    _validate_password(data.new_password, data.confirm_password)
    if not verify_password(data.current_password, principal.user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if data.new_password == data.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current password.")
    try:
        principal.user.password_hash = hash_password(data.new_password)
        principal.user.token_version = (principal.user.token_version or 0) + 1
        revoke_user_sessions(db, principal.user.user_id)
        write_audit_event(db, "password_changed", user_id=principal.user.user_id, workspace_id=principal.workspace_id)
        db.commit()
        clear_session_cookies(response)
        return {"message": "Password changed successfully. Please sign in again."}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to change the password right now. Please try again.") from exc


@router.post("/forgot-password", response_model=RecoveryChallengeResponse, status_code=status.HTTP_202_ACCEPTED)
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    provider: SmsProvider = Depends(get_sms_provider),
):
    require_trusted_origin(request)
    try:
        mobile_e164 = normalize_mobile(data.mobile_number)
    except HTTPException:
        return {"message": _GENERIC_RECOVERY_DETAIL, "challenge_id": uuid4()}
    try:
        user = db.execute(
            select(User).where(User.mobile_e164 == mobile_e164, User.mobile_verified_at.is_not(None), User.status == "ACTIVE")
        ).scalar_one_or_none()
        challenge_id = uuid4()
        if user is not None:
            challenge = start_otp_challenge(
                db, provider, purpose="PASSWORD_RESET", mobile_e164=mobile_e164, user_id=user.user_id, client_ip=_client_ip(request)
            )
            challenge_id = challenge.public_id
            db.commit()
        return {"message": _GENERIC_RECOVERY_DETAIL, "challenge_id": challenge_id}
    except HTTPException as exc:
        db.rollback()
        return {"message": _GENERIC_RECOVERY_DETAIL, "challenge_id": uuid4()}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to start password recovery right now. Please try again.") from exc


@router.post("/reset-password/verify-otp", response_model=ResetGrantResponse)
def verify_password_reset_otp(
    data: OtpVerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_trusted_origin(request)
    try:
        challenge = verify_otp_challenge(
            db, public_id=data.challenge_id, code=data.code, purpose="PASSWORD_RESET", client_ip=_client_ip(request)
        )
        if challenge.user_id is None:
            raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
        raw_grant = create_reset_grant(db, challenge.user_id)
        write_audit_event(db, "password_reset_verified", user_id=challenge.user_id)
        db.commit()
        return ResetGrantResponse(reset_grant=raw_grant, expires_in=settings.PASSWORD_RESET_GRANT_MINUTES * 60)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to verify your code right now. Please try again.") from exc


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_trusted_origin(request)
    _validate_password(data.new_password, data.confirm_password)
    now = utc_now()
    try:
        grant = db.execute(
            select(PasswordResetGrant)
            .where(PasswordResetGrant.token_hash == hash_reset_or_invitation_token(data.reset_grant))
            .with_for_update()
        ).scalar_one_or_none()
        if grant is None or grant.consumed_at is not None or as_utc(grant.expires_at) <= now:
            raise HTTPException(status_code=400, detail="Your password reset request is invalid or expired.")
        user = db.get(User, grant.user_id)
        if user is None or user.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Your password reset request is invalid or expired.")
        user.password_hash = hash_password(data.new_password)
        user.token_version = (user.token_version or 0) + 1
        grant.consumed_at = now
        db.execute(
            select(PasswordResetGrant).where(PasswordResetGrant.user_id == user.user_id).with_for_update()
        )
        db.query(PasswordResetGrant).filter(
            PasswordResetGrant.user_id == user.user_id,
            PasswordResetGrant.consumed_at.is_(None),
        ).update({PasswordResetGrant.consumed_at: now}, synchronize_session=False)
        revoke_user_sessions(db, user.user_id, now=now)
        write_audit_event(db, "password_reset_completed", user_id=user.user_id)
        db.commit()
        return {"message": "Password reset successfully. Please sign in."}
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to reset the password right now. Please try again.") from exc


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(principal: AuthPrincipal = Depends(get_current_principal), db: Session = Depends(get_db)):
    return db.execute(
        select(AuthSession)
        .where(AuthSession.user_id == principal.user.user_id, AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.created_at.desc())
    ).scalars().all()


@router.delete("/sessions/{session_id}", response_model=MessageResponse, dependencies=[Depends(csrf_protect)])
def revoke_session(
    session_id: int,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    session = db.execute(
        select(AuthSession).where(AuthSession.session_id == session_id, AuthSession.user_id == principal.user.user_id).with_for_update()
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    session.revoked_at = utc_now()
    write_audit_event(db, "session_revoked", user_id=principal.user.user_id, workspace_id=session.workspace_id)
    db.commit()
    return {"message": "Session revoked successfully."}
