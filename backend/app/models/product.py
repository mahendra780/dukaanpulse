from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.workspace_scope import WorkspaceScoped


class Product(WorkspaceScoped, Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("workspace_id", "sku", name="uq_products_workspace_sku"),)

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True
    )

    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("categories.category_id"),
        nullable=False
    )

    brand_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    sku: Mapped[str] = mapped_column(
        String(50),
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

    category = relationship(
        "Category",
        back_populates="products"
    )
    packaging = relationship(
        "ProductPackaging",
        back_populates="product"
    )
    purchases = relationship(
        "PurchaseItem",
        back_populates="product"
    )
    inventory_movements = relationship(
        "InventoryMovement",
        back_populates="product"
    )
    order_items = relationship(
        "OrderItem",
        back_populates="product"
    )
    invoice_items = relationship(
    "InvoiceItem",
    back_populates="product"
    )
    return_items = relationship(
    "ReturnItem",
    back_populates="product",
    overlaps="packaging,return_items"
    )
