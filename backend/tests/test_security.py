import os
import subprocess
import sys
import unittest
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@localhost/test"

from app.core.security import (
    constant_time_matches,
    generate_otp,
    generate_secret,
    hash_otp,
    hash_password,
    hash_session_token,
    verify_password,
    verify_password_against_dummy,
)


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]


class PasswordAndSecretSecurityTests(unittest.TestCase):
    def test_password_hash_round_trip_and_dummy_check(self):
        password_hash = hash_password("correct-horse-battery-staple")
        self.assertNotEqual(password_hash, "correct-horse-battery-staple")
        self.assertTrue(verify_password("correct-horse-battery-staple", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))
        self.assertIsNone(verify_password_against_dummy("wrong-password"))

    def test_session_and_otp_values_are_random_and_only_keyed_hashes_are_compared(self):
        session_token = generate_secret()
        self.assertNotEqual(session_token, generate_secret())
        self.assertNotEqual(session_token, hash_session_token(session_token))
        self.assertTrue(constant_time_matches(hash_session_token(session_token), hash_session_token(session_token)))

        code = generate_otp()
        self.assertRegex(code, r"^[0-9]{6}$")
        self.assertNotEqual(hash_otp("challenge-a", code), hash_otp("challenge-b", code))


class ProductionConfigurationTests(unittest.TestCase):
    def run_import(self, extra_environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        environment = {
            "DATABASE_URL": "postgresql+psycopg://test:test@localhost/test",
            "PYTHONPATH": str(BACKEND_DIRECTORY),
            "PATH": os.environ["PATH"],
            "ENVIRONMENT": "production",
            "DUKAANPULSE_ENV_FILE": str(BACKEND_DIRECTORY / ".does-not-exist"),
        }
        for key in ("SYSTEMROOT", "WINDIR"):
            if key in os.environ:
                environment[key] = os.environ[key]
        environment.update(extra_environment)
        return subprocess.run(
            [sys.executable, "-c", "import app.main; print('ok')"],
            cwd=BACKEND_DIRECTORY,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_production_requires_explicit_session_and_otp_keys(self):
        result = self.run_import({})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SESSION_TOKEN_PEPPER", result.stderr)

    def test_production_requires_secure_cookie_and_sms_configuration(self):
        result = self.run_import(
            {
                "SESSION_TOKEN_PEPPER": "s" * 32,
                "OTP_HMAC_KEY": "o" * 32,
                "SMS_PROVIDER": "generic_http",
                "SMS_HTTP_URL": "https://sms.invalid/send",
                "SMS_HTTP_AUTHORIZATION": "test-only",
                "COOKIE_SECURE": "false",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("COOKIE_SECURE", result.stderr)

    def test_production_imports_only_with_complete_security_configuration_and_disables_docs(self):
        result = self.run_import(
            {
                "SESSION_TOKEN_PEPPER": "s" * 32,
                "OTP_HMAC_KEY": "o" * 32,
                "SMS_PROVIDER": "generic_http",
                "SMS_HTTP_URL": "https://sms.invalid/send",
                "SMS_HTTP_AUTHORIZATION": "test-only",
                "COOKIE_SECURE": "true",
            }
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
