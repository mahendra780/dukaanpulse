from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


from app.db.database import Base


class Purchase(Base):
    __tablename__ = "purchases"

    purchase_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    supplier_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("suppliers.supplier_id"),
        nullable=False
    )

    purchase_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    supplier_invoice_no: Mapped[str] = mapped_column(
        String(100),
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
        default="PENDING"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    supplier = relationship(
        "Supplier",
        back_populates="purchases"
    )

    items = relationship(
        "PurchaseItem",
        back_populates="purchase",
        cascade="all, delete-orphan"
    )


class PurchaseItem(Base):
    __tablename__ = "purchase_items"

    purchase_item_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    purchase_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("purchases.purchase_id"),
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

    received_quantity: Mapped[float] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=0
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

    purchase = relationship(
        "Purchase",
        back_populates="items"
    )
    product = relationship(
        "Product",
        back_populates="purchases"
    )
    packaging = relationship(
        "ProductPackaging",
        back_populates="purchase_items"
    )
  