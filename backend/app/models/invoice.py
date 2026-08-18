from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orders.order_id"),
        nullable=False
    )

    invoice_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True
    )

    invoice_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    subtotal: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    discount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    tax: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UNPAID"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    order = relationship(
        "Order",
        back_populates="invoices"
    )

    items = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    delivery = relationship(
    "Delivery",
    back_populates="invoice",
    uselist=False
    )
    payments = relationship(
    "Payment",
    back_populates="invoice",
    cascade="all, delete-orphan"
    )
    returns = relationship(
    "Return",
    back_populates="invoice"
    )



class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    invoice_item_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    invoice_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("invoices.invoice_id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("products.product_id"),
        nullable=False
    )

    packaging_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("product_packaging.packaging_id"),
        nullable=False
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False
    )

    unit_price: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    discount: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    tax: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0
    )

    line_total: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )

    invoice = relationship(
        "Invoice",
        back_populates="items"
    )

    product = relationship(
        "Product",
        back_populates="invoice_items"
    )

    packaging = relationship(
        "ProductPackaging",
        back_populates="invoice_items"
    )