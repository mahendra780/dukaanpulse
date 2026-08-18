from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    movement_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("products.product_id"),
        nullable=False
    )

    base_quantity: Mapped[float] = mapped_column(
        Numeric(14, 3),
        nullable=False
    )

    movement_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    movement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    purchase_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("purchase_items.purchase_item_id"),
        nullable=True
    )

    invoice_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True
    )

    return_item_id: Mapped[int | None] = mapped_column(
        BigInteger,
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

    product = relationship(
        "Product",
        back_populates="inventory_movements"
    )