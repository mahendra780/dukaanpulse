from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Return(Base):
    __tablename__ = "returns"

    return_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("invoices.invoice_id"),
        nullable=False
    )

    return_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="REQUESTED"
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
        back_populates="returns"
    )

    items = relationship(
        "ReturnItem",
        back_populates="return_record",
        cascade="all, delete-orphan"
    )


class ReturnItem(Base):
    __tablename__ = "return_items"

    __table_args__ = (
        ForeignKeyConstraint(
            ["packaging_id", "product_id"],
            [
                "product_packaging.packaging_id",
                "product_packaging.product_id",
            ],
            name="fk_return_item_packaging",
        ),
    )

    return_item_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    return_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("returns.return_id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("products.product_id"),
        nullable=False
    )

    packaging_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )

    condition: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    return_record = relationship(
        "Return",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="return_items",
        overlaps="return_items,packaging"
    )

    packaging = relationship(
        "ProductPackaging",
        back_populates="return_items",
        overlaps="product,return_items"
    )