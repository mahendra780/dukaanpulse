from sqlalchemy import BigInteger, Boolean, ForeignKey, Identity, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ProductPackaging(Base):
    __tablename__ = "product_packaging"
    __table_args__ = (
        UniqueConstraint("packaging_id", "product_id", name="uq_packaging_product_pair"),
        UniqueConstraint("product_id", "unit_name", name="uq_product_unit"),
        Index("idx_packaging_product", "product_id"),
        Index(
            "uq_one_base_unit_per_product",
            "product_id",
            unique=True,
            postgresql_where=text("is_base_unit = true"),
        ),
    )

    packaging_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("products.product_id"),
        nullable=False
    )

    unit_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False
    )

    conversion_to_base: Mapped[float] = mapped_column(
        Numeric(12, 4),
        nullable=False
    )

    is_base_unit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    is_purchase_unit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    is_sale_unit: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    product = relationship(
        "Product",
        back_populates="packaging"
    )
    purchase_items = relationship(
        "PurchaseItem",
        back_populates="packaging",
        overlaps="purchases"
    )
    order_items = relationship(
        "OrderItem",
        back_populates="packaging",
        overlaps="order_items"
    )
    invoice_items = relationship(
        "InvoiceItem",
        back_populates="packaging",
        overlaps="invoice_items"
    )
    return_items = relationship(
    "ReturnItem",
    back_populates="packaging",
    overlaps="product,return_items"
    )
