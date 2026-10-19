import secrets
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError, InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings


class AccessTokenError(Exception):
    """Base class for access-token validation errors."""


class ExpiredAccessTokenError(AccessTokenError):
    """Raised when an otherwise valid access token has expired."""


class InvalidAccessTokenSignatureError(AccessTokenError):
    """Raised when a token signature does not match the configured signing key."""


class MalformedAccessTokenError(AccessTokenError):
    """Raised when an access token cannot be decoded or has invalid claims."""


password_hasher = PasswordHash.recommended()
_dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def verify_password_against_dummy(password: str) -> None:
    password_hasher.verify(password, _dummy_password_hash)


def create_access_token(user_id: int) -> str:
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": issued_at,
            "exp": expires_at,
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, object]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["sub", "iat", "exp"]},
        )
    except ExpiredSignatureError as exc:
        raise ExpiredAccessTokenError("Access token has expired.") from exc
    except InvalidSignatureError as exc:
        raise InvalidAccessTokenSignatureError(
            "Access token signature is invalid. It may have been tampered with "
            "or signed with a different key."
        ) from exc
    except InvalidTokenError as exc:
        raise MalformedAccessTokenError(
            "Access token is malformed or has invalid claims."
        ) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise MalformedAccessTokenError("Access token has an invalid subject claim.")

    return payload
