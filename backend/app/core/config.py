from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_DEFAULT_CORS_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=480, gt=0)
    ENVIRONMENT: Literal["development", "production"] = "development"
    CORS_ALLOWED_ORIGINS: str = _DEFAULT_CORS_ALLOWED_ORIGINS

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_allowed_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin.")
        return ",".join(origins)

    @property
    def cors_allowed_origins(self) -> list[str]:
        return self.CORS_ALLOWED_ORIGINS.split(",")


settings = Settings()
