import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ConfigEnvironmentFileTests(unittest.TestCase):
    def test_dukaanpulse_env_file_selects_the_settings_file(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env.demo"
            env_file.write_text(
                "\n".join(
                    (
                        "DATABASE_URL=postgresql+psycopg://demo:demo@localhost/demo",
                        "SESSION_TOKEN_PEPPER=this-is-a-test-only-session-key-with-more-than-32-characters",
                        "OTP_HMAC_KEY=this-is-a-test-only-otp-key-with-more-than-32-characters",
                        "COOKIE_SECURE=true",
                        "SMS_PROVIDER=generic_http",
                        "SMS_HTTP_URL=https://sms.invalid/send",
                        "SMS_HTTP_AUTHORIZATION=test-only",
                        "ENVIRONMENT=production",
                    )
                ),
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["DUKAANPULSE_ENV_FILE"] = str(env_file)
            environment.pop("DATABASE_URL", None)
            environment.pop("JWT_SECRET_KEY", None)
            environment.pop("SESSION_TOKEN_PEPPER", None)
            environment.pop("OTP_HMAC_KEY", None)
            environment.pop("COOKIE_SECURE", None)
            environment.pop("SMS_PROVIDER", None)
            environment.pop("SMS_HTTP_URL", None)
            environment.pop("SMS_HTTP_AUTHORIZATION", None)
            environment.pop("ENVIRONMENT", None)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from app.core.config import settings; print(settings.ENVIRONMENT)",
                ],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                capture_output=True,
                text=True,
                check=True,
            )

        self.assertEqual(result.stdout.strip(), "production")

    def test_invalid_business_timezone_prevents_startup_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env.invalid-timezone"
            env_file.write_text(
                "\n".join(
                    (
                        "DATABASE_URL=postgresql+psycopg://demo:demo@localhost/demo",
                        "SESSION_TOKEN_PEPPER=this-is-a-test-only-session-key-with-more-than-32-characters",
                        "OTP_HMAC_KEY=this-is-a-test-only-otp-key-with-more-than-32-characters",
                        "BUSINESS_TIMEZONE=Not/ARealTimezone",
                    )
                ),
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["DUKAANPULSE_ENV_FILE"] = str(env_file)
            environment.pop("DATABASE_URL", None)
            environment.pop("JWT_SECRET_KEY", None)
            environment.pop("BUSINESS_TIMEZONE", None)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from app.core.config import settings",
                ],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "BUSINESS_TIMEZONE must be a valid IANA timezone name.",
            result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
