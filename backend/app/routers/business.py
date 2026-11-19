from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, csrf_protect, get_current_principal, require_trusted_origin, require_workspace
from app.core.mobile import normalize_mobile
from app.core.permissions import permissions_for_principal, require_permission
from app.core.roles import WORKSPACE_ROLES
from app.core.config import settings
from app.core.security import (
    generate_secret,
    hash_password,
    hash_reset_or_invitation_token,
    verify_password,
    verify_password_against_dummy,
)
from app.db.database import get_db
from app.models.auth_lifecycle import OtpChallenge, WorkspaceInvitation
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMembership
from app.schemas.auth import ChallengeResponse, CurrentUserResponse, WorkspaceSummary
from app.schemas.business import (
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationCreateResponse,
    InvitationVerifyRequest,
)
from app.services.auth_lifecycle import (
    issue_session,
    as_utc,
    set_session_cookies,
    start_otp_challenge,
    utc_now,
    verify_otp_challenge,
    write_audit_event,
)
from app.services.sms_provider import SmsProvider, get_sms_provider


router = APIRouter(prefix="/business", tags=["Business"])
_ASSIGNABLE_ROLES = frozenset(WORKSPACE_ROLES) - {"OWNER"}


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _validate_pending_user(data: InvitationAcceptRequest) -> tuple[str, str, str]:
    if not data.full_name or not data.full_name.strip() or len(data.full_name.strip()) > 100:
        raise HTTPException(status_code=400, detail="Full name is required.")
    if not data.username or not data.username.strip() or len(data.username.strip()) > 50:
        raise HTTPException(status_code=400, detail="Username is required.")
    if not data.password or not data.confirm_password:
        raise HTTPException(status_code=400, detail="Password is required.")
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if len(data.password) < 12:
        raise HTTPException(status_code=400, detail="Password must be at least 12 characters long.")
    return data.full_name.strip(), data.username.strip(), data.password


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_workspace), Depends(csrf_protect)],
)
def create_invitation(
    data: InvitationCreateRequest,
    principal: AuthPrincipal = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    if principal.workspace_id is None:
        raise HTTPException(status_code=403, detail="Select an active workspace to continue.")
    if data.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="Choose a valid staff role.")
    mobile_e164 = normalize_mobile(data.mobile_number)
    now = utc_now()
    try:
        existing = db.execute(
            select(WorkspaceInvitation).where(
                WorkspaceInvitation.workspace_id == principal.workspace_id,
                WorkspaceInvitation.mobile_e164 == mobile_e164,
                WorkspaceInvitation.accepted_at.is_(None),
                WorkspaceInvitation.revoked_at.is_(None),
                WorkspaceInvitation.expires_at > now,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="An active invitation already exists for this mobile number.")
        token = generate_secret()
        invitation = WorkspaceInvitation(
            workspace_id=principal.workspace_id,
            created_by_user_id=principal.user.user_id,
            mobile_e164=mobile_e164,
            role=data.role,
            token_hash=hash_reset_or_invitation_token(token),
            expires_at=now + timedelta(days=7),
        )
        db.add(invitation)
        write_audit_event(
            db,
            "invitation_created",
            user_id=principal.user.user_id,
            workspace_id=principal.workspace_id,
            detail=data.role,
        )
        db.commit()
        return InvitationCreateResponse(invitation_token=token, expires_at=invitation.expires_at)
    except HTTPException:
        db.rollback()
        raise
    except (IntegrityError, SQLAlchemyError) as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create the invitation right now. Please try again.") from exc


@router.post("/invitations/accept", response_model=ChallengeResponse, status_code=status.HTTP_202_ACCEPTED)
def accept_invitation(
    data: InvitationAcceptRequest,
    request: Request,
    db: Session = Depends(get_db),
    provider: SmsProvider = Depends(get_sms_provider),
):
    require_trusted_origin(request)
    now = utc_now()
    try:
        invitation = db.execute(
            select(WorkspaceInvitation)
            .where(WorkspaceInvitation.token_hash == hash_reset_or_invitation_token(data.invitation_token))
            .with_for_update()
        ).scalar_one_or_none()
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.revoked_at is not None
            or as_utc(invitation.expires_at) <= now
        ):
            raise HTTPException(status_code=400, detail="This invitation is invalid or expired.")
        existing_user = db.execute(
            select(User).where(User.mobile_e164 == invitation.mobile_e164).with_for_update()
        ).scalar_one_or_none()
        pending_full_name = pending_username = pending_password_hash = None
        if existing_user is None:
            pending_full_name, pending_username, password = _validate_pending_user(data)
            duplicate = db.execute(
                select(User.user_id).where(func.lower(User.username) == pending_username.lower())
            ).scalar_one_or_none()
            if duplicate is not None:
                raise HTTPException(status_code=409, detail="This username cannot be used.")
            pending_password_hash = hash_password(password)
        else:
            # Existing account: OTP alone must not sign the user in. Require the
            # account's current password first, with the same lockout as login.
            if existing_user.locked_until is not None and as_utc(existing_user.locked_until) > now:
                verify_password_against_dummy(data.password or "")
                db.commit()
                raise HTTPException(status_code=401, detail="Unable to accept this invitation.")
            if not data.password or not verify_password(data.password, existing_user.password_hash):
                existing_user.failed_login_count = (existing_user.failed_login_count or 0) + 1
                if existing_user.failed_login_count >= settings.FAILED_LOGIN_ATTEMPT_THRESHOLD:
                    existing_user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                db.commit()
                raise HTTPException(status_code=401, detail="Unable to accept this invitation.")
            existing_user.failed_login_count = 0
            existing_user.locked_until = None
        challenge = start_otp_challenge(
            db,
            provider,
            purpose="INVITATION",
            mobile_e164=invitation.mobile_e164,
            invitation_id=invitation.invitation_id,
            pending_username=pending_username,
            pending_full_name=pending_full_name,
            pending_password_hash=pending_password_hash,
            client_ip=_client_ip(request),
        )
        db.commit()
        return ChallengeResponse(challenge_id=challenge.public_id)
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to accept the invitation right now. Please try again.") from exc


@router.post("/invitations/verify-otp", response_model=CurrentUserResponse)
def verify_invitation_otp(
    data: InvitationVerifyRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    require_trusted_origin(request)
    now = utc_now()
    try:
        challenge = verify_otp_challenge(
            db, public_id=data.challenge_id, code=data.code, purpose="INVITATION", client_ip=_client_ip(request), now=now
        )
        if challenge.invitation_id is None:
            raise HTTPException(status_code=400, detail="The verification code is invalid or expired.")
        invitation = db.execute(
            select(WorkspaceInvitation).where(WorkspaceInvitation.invitation_id == challenge.invitation_id).with_for_update()
        ).scalar_one_or_none()
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.revoked_at is not None
            or as_utc(invitation.expires_at) <= now
        ):
            raise HTTPException(status_code=400, detail="This invitation is invalid or expired.")
        user = db.execute(select(User).where(User.mobile_e164 == invitation.mobile_e164).with_for_update()).scalar_one_or_none()
        if user is None:
            if not all((challenge.pending_username, challenge.pending_full_name, challenge.pending_password_hash)):
                raise HTTPException(status_code=400, detail="This invitation is invalid or expired.")
            user = User(
                username=challenge.pending_username,
                full_name=challenge.pending_full_name,
                password_hash=challenge.pending_password_hash,
                role="VIEWER",
                status="ACTIVE",
                mobile_e164=invitation.mobile_e164,
                mobile_verified_at=now,
            )
            db.add(user)
            db.flush()
        elif user.status != "ACTIVE":
            raise HTTPException(status_code=400, detail="This invitation is invalid or expired.")
        membership = db.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == invitation.workspace_id,
                WorkspaceMembership.user_id == user.user_id,
            )
        ).scalar_one_or_none()
        if membership is None:
            membership = WorkspaceMembership(
                workspace_id=invitation.workspace_id,
                user_id=user.user_id,
                role=invitation.role,
                status="ACTIVE",
            )
            db.add(membership)
        elif membership.status != "ACTIVE":
            membership.status = "ACTIVE"
            membership.role = invitation.role
        # The session does not autoflush, and issue_session looks the membership
        # up in the database. Write the new or reactivated membership first,
        # otherwise it is not found and the request fails with
        # "An active workspace membership is required."
        db.flush()
        invitation.accepted_at = now
        _, session_token, csrf_token = issue_session(db, user_id=user.user_id, workspace_id=invitation.workspace_id, now=now)
        write_audit_event(db, "invitation_accepted", user_id=user.user_id, workspace_id=invitation.workspace_id, detail=invitation.role)
        db.commit()
        workspace = db.get(Workspace, invitation.workspace_id)
        set_session_cookies(response, session_token=session_token, csrf_token=csrf_token)
        return CurrentUserResponse(
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            mobile_e164=user.mobile_e164,
            workspace=WorkspaceSummary(workspace_id=workspace.workspace_id, business_name=workspace.business_name, role=membership.role),
            memberships=[WorkspaceSummary(workspace_id=workspace.workspace_id, business_name=workspace.business_name, role=membership.role)],
            permissions=permissions_for_principal(
                AuthPrincipal(
                    user=user,
                    session=AuthSession(workspace_id=workspace.workspace_id),
                    membership=membership,
                )
            ),
        )
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Unable to accept this invitation.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to verify your invitation right now. Please try again.") from exc