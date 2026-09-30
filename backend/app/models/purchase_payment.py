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
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PurchasePayment(Base):
    __tablename__ = "purchase_payments"

    purchase_payment_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    purchase_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("purchases.purchase_id"),
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

    purchase = relationship(
        "Purchase",
        back_populates="payments"
    )