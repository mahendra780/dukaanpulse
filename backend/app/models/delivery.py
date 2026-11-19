from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.workspace_scope import WorkspaceScoped


class Delivery(WorkspaceScoped, Base):
    __tablename__ = "deliveries"
    __table_args__ = (
    Index(
        "uq_delivery_invoice_active",
        "invoice_id",
        unique=True,
        postgresql_where=(mapped_column("status") != "CANCELLED"),
        sqlite_where=(mapped_column("status") != "CANCELLED"),
    ),
)

    delivery_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("invoices.invoice_id"),
        nullable=False,
    )

    delivery_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING"
    )

    delivery_address: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    vehicle_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    driver_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    invoice = relationship(
        "Invoice",
         back_populates="deliveries",
        # uselist=False
    )
