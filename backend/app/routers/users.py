from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import  func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, get_current_principal
from app.core.permissions import require_permission
from app.core.roles import WORKSPACE_ROLES
from app.core.security import hash_password, verify_password
from app.db.database import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMembership
from app.schemas.auth import MessageResponse
from app.schemas.user import ManagedUserResponse, PasswordResetRequest, UserCreate, UserUpdate
from app.services.auth_lifecycle import revoke_user_sessions, write_audit_event


router = APIRouter(prefix="/users", tags=["Users"])
_OWNER_ROLE = "OWNER"
_ACTIVE_STATUS = "ACTIVE"
_INACTIVE_STATUS = "INACTIVE"


def _response(user: User, membership: WorkspaceMembership) -> ManagedUserResponse:
    return ManagedUserResponse(
        user_id=user.user_id,
        username=user.username,
        full_name=user.full_name,
        role=membership.role,
        status=membership.status,
        membership_status=membership.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _membership_or_404(db: Session, user_id: int, workspace_id: int) -> tuple[User, WorkspaceMembership]:
    row = db.execute(
        select(User, WorkspaceMembership)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.user_id)
        .where(WorkspaceMembership.workspace_id == workspace_id, User.user_id == user_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return row


def _ensure_owner_change_is_allowed(
    db: Session,
    *,
    membership: WorkspaceMembership,
    current_user_id: int,
    new_role: str,
    new_status: str,
) -> None:
    if membership.user_id == current_user_id:
        if new_status != "ACTIVE":
            raise HTTPException(status_code=400, detail="You cannot deactivate your own workspace membership.")
        if new_role != membership.role:
            raise HTTPException(status_code=400, detail="You cannot change your own workspace role.")
    if membership.role != _OWNER_ROLE and new_role == _OWNER_ROLE:
        raise HTTPException(status_code=400, detail="Workspace ownership changes are not supported here.")
    if membership.role == _OWNER_ROLE and membership.user_id != current_user_id:
        raise HTTPException(status_code=400, detail="Another owner's membership cannot be changed here.")
    if membership.role != _OWNER_ROLE or (new_role == _OWNER_ROLE and new_status == _ACTIVE_STATUS):
        return
    owners = db.execute(
        select(WorkspaceMembership.membership_id)
        .where(
            WorkspaceMembership.workspace_id == membership.workspace_id,
            WorkspaceMembership.role == _OWNER_ROLE,
            WorkspaceMembership.status == _ACTIVE_STATUS,
        )
        .with_for_update()
    ).scalars().all()
    if len(owners) <= 1:
        raise HTTPException(status_code=400, detail="The last active owner cannot be deactivated or demoted.")


@router.get("", response_model=list[ManagedUserResponse], dependencies=[Depends(require_permission("users:manage"))])
def get_users(
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(User, WorkspaceMembership)
        .join(WorkspaceMembership, WorkspaceMembership.user_id == User.user_id)
        .where(WorkspaceMembership.workspace_id == principal.workspace_id)
        .order_by(User.user_id)
    ).all()
    return [_response(user, membership) for user, membership in rows]


@router.post("", response_model=ManagedUserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("users:manage"))])
def create_user(data: UserCreate):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invite staff through the workspace invitation flow instead of creating accounts directly.",
    )


@router.patch("/{user_id}", response_model=ManagedUserResponse, dependencies=[Depends(require_permission("users:manage"))])
def update_user(
    user_id: int,
    data: UserUpdate,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    if principal.workspace_id is None:
        raise HTTPException(status_code=403, detail="Select an active workspace to continue.")
    if "username" in data.model_fields_set:
        raise HTTPException(status_code=400, detail="Username cannot be changed.")
    if not data.model_fields_set:
        raise HTTPException(status_code=400, detail="Provide at least one change.")
    user, membership = _membership_or_404(db, user_id, principal.workspace_id)
    full_name = user.full_name if data.full_name is None else data.full_name.strip()
    if not full_name or len(full_name) > 100:
        raise HTTPException(status_code=400, detail="Full name must be between 1 and 100 characters.")
    role = membership.role if data.role is None else data.role
    if role not in WORKSPACE_ROLES:
        raise HTTPException(status_code=400, detail="Choose a valid workspace role.")
    membership_status = membership.status if data.status is None else data.status
    if membership_status not in {_ACTIVE_STATUS, _INACTIVE_STATUS}:
        raise HTTPException(status_code=400, detail="Status must be ACTIVE or INACTIVE.")
    _ensure_owner_change_is_allowed(
        db,
        membership=membership,
        current_user_id=principal.user.user_id,
        new_role=role,
        new_status=membership_status,
    )
    try:
        user.full_name = full_name
        membership.role = role
        membership.status = membership_status
        if membership_status != _ACTIVE_STATUS:
            revoke_user_sessions(db, user.user_id)
        write_audit_event(
            db,
            "workspace_membership_updated",
            user_id=user.user_id,
            workspace_id=principal.workspace_id,
            detail=role,
        )
        db.commit()
        db.refresh(user)
        return _response(user, membership)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="User changes conflict with existing data.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update the user right now. Please try again.") from exc


@router.post("/{user_id}/reset-password", response_model=MessageResponse, dependencies=[Depends(require_permission("users:manage"))])
def reset_password(
    user_id: int,
    data: PasswordResetRequest,
    principal: AuthPrincipal = Depends(get_current_principal),
    db: Session = Depends(get_db),
):
    if principal.workspace_id is None:
        raise HTTPException(status_code=403, detail="Select an active workspace to continue.")
    if principal.membership is None or principal.membership.role != _OWNER_ROLE:
        raise HTTPException(status_code=403, detail="Only the workspace owner can reset a staff password.")
    if len(data.new_password) < 12:
        raise HTTPException(status_code=400, detail="New password must be at least 12 characters long.")
    user, _membership = _membership_or_404(db, user_id, principal.workspace_id)

    # User accounts are global. If this person also belongs to another
    # workspace, this owner must not be able to take over their account.
    if user.user_id != principal.user.user_id:
        other_workspaces = db.execute(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.user_id == user.user_id,
                WorkspaceMembership.workspace_id != principal.workspace_id,
            )
        ).scalar_one()
        if other_workspaces > 0:
            raise HTTPException(
                status_code=403,
                detail="This user belongs to other workspaces. They must reset their own password with 'Forgot password'.",
            )

    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="New password must differ from the current password.")
    try:
        user.password_hash = hash_password(data.new_password)
        user.token_version = (user.token_version or 0) + 1
        revoke_user_sessions(db, user.user_id)
        write_audit_event(
            db,
            "administrator_password_reset",
            user_id=user.user_id,
            workspace_id=principal.workspace_id,
            detail=f"by:{principal.user.user_id}",
        )
        db.commit()
        return {"message": "Password reset successfully."}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to reset the password right now. Please try again.") from exc
