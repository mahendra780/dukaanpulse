from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InvitationCreateRequest(BaseModel):
    mobile_number: str = Field(min_length=8, max_length=32)
    role: str


class InvitationCreateResponse(BaseModel):
    invitation_token: str
    expires_at: datetime


class InvitationAcceptRequest(BaseModel):
    invitation_token: str = Field(min_length=20, max_length=512)
    full_name: str | None = Field(default=None, max_length=100)
    username: str | None = Field(default=None, max_length=50)
    password: str | None = Field(default=None, max_length=1024)
    confirm_password: str | None = Field(default=None, max_length=1024)


class InvitationVerifyRequest(BaseModel):
    challenge_id: UUID
    code: str = Field(pattern=r"^[0-9]{6}$")
