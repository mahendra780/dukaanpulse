from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.permissions import require_permission
from app.core.roles import ROLES, USER_STATUSES
from app.core.security import hash_password, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    ManagedUserResponse,
    PasswordResetRequest,
    UserCreate,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["Users"])

_ADMIN_ROLE = ROLES[0]
_ACTIVE_STATUS = USER_STATUSES[0]
_INACTIVE_STATUS = USER_STATUSES[1]


def _validate_username(username: str) -> str:
    username = username.strip()
    if not username or len(username) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 1 and 50 characters.",
        )
    return username


def _validate_full_name(full_name: str) -> str:
    full_name = full_name.strip()
    if not full_name or len(full_name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be between 1 and 100 characters.",
        )
    return full_name


def _validate_role(role: str) -> str:
    if role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {', '.join(ROLES)}.",
        )
    return role


def _validate_status(user_status: str) -> str:
    if user_status not in USER_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status must be one of: {', '.join(USER_STATUSES)}.",
        )
    return user_status


def _validate_new_password(password: str, label: str) -> None:
    if len(password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{label} must be at least 10 characters long.",
        )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def _ensure_admin_change_is_allowed(
    db: Session,
    target_user: User,
    current_user: User,
    new_role: str,
    new_status: str,
) -> None:
    if target_user.user_id == current_user.user_id:
        if new_status == _INACTIVE_STATUS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account.",
            )
        if new_role != _ADMIN_ROLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own administrator role.",
            )

    is_active_admin = (
        target_user.role == _ADMIN_ROLE
        and target_user.status == _ACTIVE_STATUS
    )
    remains_active_admin = (
        new_role == _ADMIN_ROLE
        and new_status == _ACTIVE_STATUS
    )
    if not is_active_admin or remains_active_admin:
        return

    active_admins = db.execute(
        select(User.user_id)
        .where(
            User.role == _ADMIN_ROLE,
            User.status == _ACTIVE_STATUS,
        )
        .with_for_update()
    ).scalars().all()
    if len(active_admins) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The last active administrator cannot be deactivated or demoted.",
        )


@router.get(
    "",
    response_model=list[ManagedUserResponse],
    dependencies=[Depends(require_permission("users:manage"))],
)
def get_users(db: Session = Depends(get_db)):
    return db.execute(select(User).order_by(User.user_id)).scalars().all()


@router.post(
    "",
    response_model=ManagedUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users:manage"))],
)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    username = _validate_username(data.username)
    full_name = _validate_full_name(data.full_name)
    role = _validate_role(data.role)
    _validate_new_password(data.initial_password, "Initial password")

    existing_user = db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    ).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already in use.",
        )

    try:
        user = User(
            username=username,
            full_name=full_name,
            password_hash=hash_password(data.initial_password),
            role=role,
            status=_ACTIVE_STATUS,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already in use.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the user right now. Please try again.",
        ) from exc

    return user


@router.patch(
    "/{user_id}",
    response_model=ManagedUserResponse,
    dependencies=[Depends(require_permission("users:manage"))],
)
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if "username" in data.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be changed.",
        )
    if not data.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one change.",
        )

    user = _get_user_or_404(db, user_id)
    full_name = (
        _validate_full_name(data.full_name)
        if data.full_name is not None
        else user.full_name
    )
    role = _validate_role(data.role) if data.role is not None else user.role
    user_status = (
        _validate_status(data.status)
        if data.status is not None
        else user.status
    )
    _ensure_admin_change_is_allowed(
        db,
        target_user=user,
        current_user=current_user,
        new_role=role,
        new_status=user_status,
    )

    try:
        user.full_name = full_name
        user.role = role
        user.status = user_status
        db.commit()
        db.refresh(user)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User changes conflict with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the user right now. Please try again.",
        ) from exc

    return user


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    dependencies=[Depends(require_permission("users:manage"))],
)
def reset_password(
    user_id: int,
    data: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    _validate_new_password(data.new_password, "New password")
    user = _get_user_or_404(db, user_id)
    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password.",
        )

    try:
        user.password_hash = hash_password(data.new_password)
        user.token_version = (user.token_version or 0) + 1
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to reset the password right now. Please try again.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to reset the password right now. Please try again.",
        ) from exc

    return {"message": "Password reset successfully."}
