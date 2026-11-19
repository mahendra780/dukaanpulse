from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.workspace_scope import WorkspaceScoped


class Supplier(WorkspaceScoped, Base):
    __tablename__ = "suppliers"
    __table_args__ = (UniqueConstraint("workspace_id", "gst_number", name="uq_suppliers_workspace_gst"),)

    supplier_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    supplier_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    address: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    gst_number: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True
    )

    payment_terms_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
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
    purchases = relationship(
    "Purchase",
    back_populates="supplier"
    )
