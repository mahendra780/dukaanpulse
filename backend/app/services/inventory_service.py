from sqlalchemy.orm import Session

from app.models.inventory import InventoryMovement
from app.models.purchase import PurchaseItem
from fastapi import HTTPException
from sqlalchemy import select,func
from app.models.invoice import InvoiceItem


def create_purchase_movement(
    db: Session,
    purchase_item: PurchaseItem
):
    packaging = purchase_item.packaging

    base_quantity = (
        float(purchase_item.received_quantity)
        * float(packaging.conversion_to_base)
    )

    movement = InventoryMovement(
        product_id=purchase_item.product_id,
        base_quantity=base_quantity,
        movement_type="PURCHASE",
        purchase_item_id=purchase_item.purchase_item_id,
        notes=(
            f"Purchase received: "
            f"{purchase_item.received_quantity} "
            f"{packaging.unit_name}"
        )
    )

    db.add(movement)

    return movement




def create_sale_movement(
    db,
    invoice_item: InvoiceItem
):
    # Prevent duplicate sale movement
    existing = db.execute(
        select(InventoryMovement).where(
            InventoryMovement.invoice_item_id
            == invoice_item.invoice_item_id,
            InventoryMovement.movement_type == "SALE"
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Inventory sale movement already exists "
                f"for invoice item {invoice_item.invoice_item_id}"
            )
        )

    packaging = invoice_item.packaging

    base_quantity = (
        float(invoice_item.quantity)
        * float(packaging.conversion_to_base)
    )

    # Check available stock
    current_stock = db.execute(
        select(
            func.coalesce(
                func.sum(InventoryMovement.base_quantity),
                0
            )
        ).where(
            InventoryMovement.product_id
            == invoice_item.product_id
        )
    ).scalar()

    if float(current_stock) < base_quantity:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient stock for product "
                f"{invoice_item.product_id}. "
                f"Available: {float(current_stock)}, "
                f"Required: {base_quantity}"
            )
        )

    movement = InventoryMovement(
        product_id=invoice_item.product_id,
        base_quantity=-base_quantity,
        movement_type="SALE",
        invoice_item_id=invoice_item.invoice_item_id,
        notes="Sale delivered to customer"
    )

    db.add(movement)

    return movement
def create_return_movement(
    db,
    return_item
):
    from sqlalchemy import select

    # Prevent duplicate return movement
    existing = db.execute(
        select(InventoryMovement).where(
            InventoryMovement.return_item_id
            == return_item.return_item_id
        )
    ).scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Inventory return movement already exists "
                f"for return item {return_item.return_item_id}"
            )
        )

    # Only sellable returned goods come back into stock
    if return_item.condition != "RESELLABLE":
        return None

    packaging = return_item.packaging

    base_quantity = (
        float(return_item.quantity)
        * float(packaging.conversion_to_base)
    )

    movement = InventoryMovement(
        product_id=return_item.product_id,
        base_quantity=base_quantity,
        movement_type="RETURN",
        return_item_id=return_item.return_item_id,
        notes=(
            f"Customer return received: "
            f"{return_item.quantity} {packaging.unit_name}"
        )
    )

    db.add(movement)

    return movement