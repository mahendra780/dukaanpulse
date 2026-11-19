from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.workspace_scope import WorkspaceScoped


class Payment(WorkspaceScoped, Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("workspace_id", "reference_number", name="uq_payments_workspace_reference"),)

    payment_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("invoices.invoice_id"),
        nullable=False
    )

    payment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    payment_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    reference_number: Mapped[str | None] = mapped_column(
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
        back_populates="payments"
    )
