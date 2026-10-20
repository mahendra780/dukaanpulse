import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-that-is-long-enough"

import jwt

from app.core.config import settings
from app.core.security import (
    ExpiredAccessTokenError,
    InvalidAccessTokenSignatureError,
    MalformedAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
    verify_password_against_dummy,
)


TEST_DATABASE_URL = "postgresql+psycopg://test:test@localhost/test"
BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


def _run_python(statement: str, extra_environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    environment = {
        "DATABASE_URL": TEST_DATABASE_URL,
        "PATH": os.environ["PATH"],
        "PYTHONPATH": str(BACKEND_DIRECTORY),
    }
    for key in ("SYSTEMROOT", "WINDIR"):
        if key in os.environ:
            environment[key] = os.environ[key]
    environment.update(extra_environment)

    with tempfile.TemporaryDirectory() as temporary_directory:
        return subprocess.run(
            [sys.executable, "-c", statement],
            cwd=temporary_directory,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )


class PasswordSecurityTests(unittest.TestCase):
    def test_hash_round_trip(self):
        password_hash = hash_password("correct-horse-battery-staple")

        self.assertNotEqual(password_hash, "correct-horse-battery-staple")
        self.assertTrue(verify_password("correct-horse-battery-staple", password_hash))

    def test_wrong_password_is_rejected(self):
        password_hash = hash_password("correct-horse-battery-staple")

        self.assertFalse(verify_password("not-the-password", password_hash))

    def test_dummy_password_verification_does_not_accept_a_password(self):
        self.assertIsNone(verify_password_against_dummy("not-the-password"))


class AccessTokenSecurityTests(unittest.TestCase):
    def test_access_token_subject_is_a_string(self):
        payload = decode_access_token(create_access_token(123))

        self.assertEqual(payload["sub"], "123")
        self.assertIsInstance(payload["sub"], str)

    def test_expired_token_is_rejected(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "123",
                "iat": now - timedelta(minutes=2),
                "exp": now - timedelta(minutes=1),
                "token_version": 0,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )

        with self.assertRaises(ExpiredAccessTokenError):
            decode_access_token(token)

    def test_tampered_token_is_rejected(self):
        parts = create_access_token(123).split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]

        with self.assertRaises(InvalidAccessTokenSignatureError):
            decode_access_token(".".join(parts))

    def test_token_signed_with_a_different_key_is_rejected(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode(
            {
                "sub": "123",
                "iat": now,
                "exp": now + timedelta(minutes=1),
                "token_version": 0,
            },
            "different-test-jwt-secret-key-that-is-long-enough",
            algorithm=settings.ALGORITHM,
        )

        with self.assertRaises(InvalidAccessTokenSignatureError):
            decode_access_token(token)

    def test_malformed_token_is_rejected(self):
        with self.assertRaises(MalformedAccessTokenError):
            decode_access_token("not-a-token")


class SettingsSecurityTests(unittest.TestCase):
    def test_missing_jwt_secret_key_is_rejected(self):
        result = _run_python("import app.main", {})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JWT_SECRET_KEY", result.stderr)

    def test_short_jwt_secret_key_is_rejected(self):
        result = _run_python("import app.main", {"JWT_SECRET_KEY": "too-short"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("JWT_SECRET_KEY", result.stderr)

    def test_application_imports_with_a_valid_jwt_secret_key(self):
        result = _run_python(
            "import app.main",
            {"JWT_SECRET_KEY": "test-jwt-secret-key-that-is-long-enough"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_disables_api_documentation_routes(self):
        result = _run_python(
            "from app.main import app; assert app.docs_url is None; assert app.redoc_url is None; assert app.openapi_url is None",
            {
                "JWT_SECRET_KEY": "test-jwt-secret-key-that-is-long-enough",
                "ENVIRONMENT": "production",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
