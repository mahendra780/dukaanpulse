from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.permissions import permissions_for_role
from app.core.roles import USER_STATUSES
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    verify_password_against_dummy,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    ChangePasswordRequest,
    CurrentUserResponse,
    MessageResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

_INVALID_CREDENTIALS_DETAIL = "Incorrect username or password."
_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def _invalid_credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_INVALID_CREDENTIALS_DETAIL,
        headers=_BEARER_CHALLENGE,
    )


@router.post("/login", response_model=AccessTokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    username = form_data.username.strip()
    user = db.execute(
        select(User)
        .where(func.lower(User.username) == username.lower())
        .with_for_update()
    ).scalar_one_or_none()

    if user is None:
        verify_password_against_dummy(form_data.password)
        raise _invalid_credentials_error()

    now = datetime.now(timezone.utc)
    if user.locked_until is not None and user.locked_until > now:
        verify_password_against_dummy(form_data.password)
        raise _invalid_credentials_error()

    password_is_valid = verify_password(form_data.password, user.password_hash)
    if not password_is_valid:
        if user.status == USER_STATUSES[0]:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.FAILED_LOGIN_ATTEMPT_THRESHOLD:
                user.locked_until = now + timedelta(
                    minutes=settings.LOGIN_LOCKOUT_MINUTES
                )

            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Unable to sign in right now. Please try again.",
                ) from exc
            except SQLAlchemyError as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unable to sign in right now. Please try again.",
                ) from exc

        raise _invalid_credentials_error()

    if user.status != USER_STATUSES[0]:
        raise _invalid_credentials_error()

    try:
        user.last_login_at = datetime.now(timezone.utc)
        user.failed_login_count = 0
        user.locked_until = None
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to sign in right now. Please try again.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to sign in right now. Please try again.",
        ) from exc

    return {
        "access_token": create_access_token(
            user.user_id,
            user.token_version or 0,
        ),
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=CurrentUserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "status": current_user.status,
        "permissions": permissions_for_role(current_user.role),
    }


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not data.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is required.",
        )

    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if data.new_password == data.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password.",
        )

    if len(data.new_password) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 10 characters long.",
        )

    try:
        current_user.password_hash = hash_password(data.new_password)
        current_user.token_version = (current_user.token_version or 0) + 1
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to change the password right now. Please try again.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to change the password right now. Please try again.",
        ) from exc

    return {"message": "Password changed successfully."}
