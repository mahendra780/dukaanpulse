from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.workspace_scope import WorkspaceScoped


class Category(WorkspaceScoped, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("workspace_id", "category_name", name="uq_categories_workspace_name"),)

    category_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    category_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    products = relationship(
    "Product",
    back_populates="category"
    )
