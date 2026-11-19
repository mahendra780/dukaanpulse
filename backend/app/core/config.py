import os
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_CORS_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
_ENV_FILE = os.environ.get("DUKAANPULSE_ENV_FILE", ".env")


class Settings(BaseSettings):
    DATABASE_URL: str
    # JWT settings remain temporarily accepted so existing deployment files do
    # not fail before the reviewed session migration is applied. Browser
    # authentication does not use JWTs.
    JWT_SECRET_KEY: str | None = Field(default=None, min_length=32)
    SESSION_TOKEN_PEPPER: str | None = Field(default=None, min_length=32)
    OTP_HMAC_KEY: str | None = Field(default=None, min_length=32)
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=480, gt=0)
    SESSION_IDLE_MINUTES: int = Field(default=30, gt=0)
    SESSION_ABSOLUTE_HOURS: int = Field(default=8, gt=0)
    PASSWORD_RESET_GRANT_MINUTES: int = Field(default=10, gt=0)
    FAILED_LOGIN_ATTEMPT_THRESHOLD: int = Field(default=5, ge=1)
    LOGIN_LOCKOUT_MINUTES: int = Field(default=15, gt=0)
    ENVIRONMENT: Literal["development", "production"] = "development"
    CORS_ALLOWED_ORIGINS: str = _DEFAULT_CORS_ALLOWED_ORIGINS
    COOKIE_NAME: str = "dukaanpulse_session"
    CSRF_COOKIE_NAME: str = "dukaanpulse_csrf"
    COOKIE_DOMAIN: str | None = None
    COOKIE_SECURE: bool | None = None
    SMS_PROVIDER: Literal["disabled", "generic_http", "console"] = "disabled"
    SMS_HTTP_URL: str | None = None
    SMS_HTTP_AUTHORIZATION: str | None = None
    DEMO_SEED_ALLOWED: bool = False
    BUSINESS_TIMEZONE: str = Field(default="Asia/Kolkata", validate_default=True)

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        extra="ignore"
    )

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin.")
        if "*" in origins:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot contain '*' when credentials are enabled.")
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.ENVIRONMENT != "production":
            return self
        if not self.SESSION_TOKEN_PEPPER or not self.OTP_HMAC_KEY:
            raise ValueError("SESSION_TOKEN_PEPPER and OTP_HMAC_KEY are required in production.")
        if not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be enabled in production.")
        if self.SMS_PROVIDER == "console":
            raise ValueError("Console SMS provider is not allowed in production.")
        if self.SMS_PROVIDER == "disabled":
            raise ValueError("SMS_PROVIDER must be configured in production.")
        if self.SMS_PROVIDER == "generic_http" and (
            not self.SMS_HTTP_URL or not self.SMS_HTTP_AUTHORIZATION
        ):
            raise ValueError(
                "SMS_HTTP_URL and SMS_HTTP_AUTHORIZATION are required for generic_http SMS."
            )
        return self

    @field_validator("BUSINESS_TIMEZONE")
    @classmethod
    def validate_business_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("BUSINESS_TIMEZONE must be a valid IANA timezone name.") from exc
        return value

    @property
    def cors_allowed_origins(self) -> list[str]:
        return self.CORS_ALLOWED_ORIGINS.split(",")

    @property
    def cookie_secure(self) -> bool:
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.ENVIRONMENT == "production"


settings = Settings()
