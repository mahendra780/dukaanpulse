from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    challenge_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    public_id: Mapped[UUID] = mapped_column(nullable=False, unique=True)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    mobile_e164: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    otp_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True)
    invitation_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("workspace_invitations.invitation_id"), nullable=True)
    pending_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pending_full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pending_business_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    pending_password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(nullable=False, server_default="0")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetGrant(Base):
    __tablename__ = "password_reset_grants"

    grant_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    invitation_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=False)
    mobile_e164: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SecurityAuditEvent(Base):
    __tablename__ = "security_audit_events"

    event_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id"), nullable=True, index=True)
    workspace_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("workspaces.workspace_id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuthRateLimitEvent(Base):
    __tablename__ = "auth_rate_limit_events"

    rate_limit_event_id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    scope: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
