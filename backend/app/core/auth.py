from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.roles import USER_STATUSES
from app.core.security import (
    AccessTokenError,
    ExpiredAccessTokenError,
    decode_access_token,
)
from app.db.database import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
_BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers=_BEARER_CHALLENGE,
    )


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _authentication_error("Authentication is required. Please sign in.")

    try:
        payload = decode_access_token(token)
    except ExpiredAccessTokenError as exc:
        raise _authentication_error(
            "Your session has expired. Please sign in again."
        ) from exc
    except AccessTokenError as exc:
        raise _authentication_error(
            "Your session is invalid. Please sign in again."
        ) from exc

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _authentication_error(
            "Your session is invalid. Please sign in again."
        ) from exc

    user = db.get(User, user_id)
    if user is None or user.status != USER_STATUSES[0]:
        raise _authentication_error(
            "Your session is no longer active. Please sign in again."
        )

    return user
