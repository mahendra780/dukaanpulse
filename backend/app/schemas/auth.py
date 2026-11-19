from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    business_name: str = Field(min_length=1, max_length=150)
    mobile_number: str = Field(min_length=8, max_length=32)
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=1024)
    confirm_password: str = Field(min_length=1, max_length=1024)


class OtpVerifyRequest(BaseModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$")


class OtpResendRequest(BaseModel):
    challenge_id: UUID


class ChallengeResponse(BaseModel):
    challenge_id: UUID
    expires_in: int = 300
    resend_after: int = 30


class WorkspaceSummary(BaseModel):
    workspace_id: int
    business_name: str
    role: str


class CurrentUserResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    mobile_e164: str | None
    workspace: WorkspaceSummary | None
    memberships: list[WorkspaceSummary]
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)
    confirm_password: str = Field(min_length=1, max_length=1024)


class ForgotPasswordRequest(BaseModel):
    mobile_number: str = Field(min_length=8, max_length=32)


class ResetPasswordRequest(BaseModel):
    reset_grant: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=1, max_length=1024)
    confirm_password: str = Field(min_length=1, max_length=1024)


class ResetGrantResponse(BaseModel):
    reset_grant: str
    expires_in: int


class RecoveryChallengeResponse(BaseModel):
    message: str
    challenge_id: UUID
    expires_in: int = 300
    resend_after: int = 30


class MessageResponse(BaseModel):
    message: str


class SessionResponse(BaseModel):
    session_id: int
    workspace_id: int
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: int
