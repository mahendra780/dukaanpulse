from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.roles import ROLES, USER_STATUSES
from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN (" + ", ".join(f"'{role}'" for role in ROLES) + ")",
            name="chk_users_role",
        ),
        CheckConstraint(
            "status IN (" + ", ".join(f"'{status}'" for status in USER_STATUSES) + ")",
            name="chk_users_status",
        ),
        Index("uq_users_username_lower", text("lower(username)"), unique=True),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=USER_STATUSES[0],
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
