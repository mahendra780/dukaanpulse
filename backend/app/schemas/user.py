from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    full_name: str
    role: str
    initial_password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    status: str | None = None
    username: str | None = None


class PasswordResetRequest(BaseModel):
    new_password: str


class ManagedUserResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str
    status: str
    created_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
