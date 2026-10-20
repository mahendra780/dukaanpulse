from typing import Literal

from pydantic import BaseModel, ConfigDict


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int


class CurrentUserResponse(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str
    status: str
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str