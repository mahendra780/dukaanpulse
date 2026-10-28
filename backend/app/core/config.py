import os
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_CORS_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
_ENV_FILE = os.environ.get("DUKAANPULSE_ENV_FILE", ".env")


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=480, gt=0)
    FAILED_LOGIN_ATTEMPT_THRESHOLD: int = Field(default=5, ge=1)
    LOGIN_LOCKOUT_MINUTES: int = Field(default=15, gt=0)
    ENVIRONMENT: Literal["development", "production"] = "development"
    CORS_ALLOWED_ORIGINS: str = _DEFAULT_CORS_ALLOWED_ORIGINS
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
        return ",".join(origins)

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


settings = Settings()
