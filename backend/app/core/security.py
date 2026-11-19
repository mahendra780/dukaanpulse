import hashlib
import hmac
import secrets

from pwdlib import PasswordHash

from app.core.config import settings


password_hasher = PasswordHash.recommended()
_dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))
# Development can deliberately use a process-local key so a fresh checkout
# remains runnable before an operator creates its local configuration. It is
# never persisted or exposed, so restarting invalidates local sessions. The
# production settings validator requires explicit configured keys.
_development_auth_key = secrets.token_urlsafe(48)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def verify_password_against_dummy(password: str) -> None:
    password_hasher.verify(password, _dummy_password_hash)


def generate_secret() -> str:
    return secrets.token_urlsafe(32)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _keyed_hash(key: str | None, value: str) -> str:
    if not key:
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("The required authentication secret is not configured.")
        key = _development_auth_key
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_session_token(token: str) -> str:
    return _keyed_hash(settings.SESSION_TOKEN_PEPPER, token)


def hash_csrf_token(token: str) -> str:
    return _keyed_hash(settings.SESSION_TOKEN_PEPPER, f"csrf:{token}")


def hash_otp(challenge_public_id: str, code: str) -> str:
    return _keyed_hash(settings.OTP_HMAC_KEY, f"otp:{challenge_public_id}:{code}")


def hash_reset_or_invitation_token(token: str) -> str:
    return _keyed_hash(settings.SESSION_TOKEN_PEPPER, f"grant:{token}")


def constant_time_matches(expected_hash: str, actual_hash: str) -> bool:
    return hmac.compare_digest(expected_hash, actual_hash)
