from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query,Body
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session,joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.purchase import Purchase, PurchaseItem
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.models.supplier import Supplier
from app.schemas.purchase import PurchaseCreate, PurchaseReceive
from app.services.inventory_service import create_purchase_movement
from app.services.purchase_service import recalculate_purchase_status
from app.services.status_rules import ensure_active_supplier, ensure_active_products

router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"]
)


@router.post("/", status_code=201, dependencies=[Depends(require_permission("purchases:write"))])
def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db)
):
    ensure_active_supplier(db, data.supplier_id, "purchase")
    ensure_active_products(db, [item.product_id for item in data.items], "purchase")
    supplier = db.get(Supplier, data.supplier_id)

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )


    existing_purchase = db.execute(
        select(Purchase).where(
            Purchase.supplier_id == data.supplier_id,
            Purchase.supplier_invoice_no == data.supplier_invoice_no
        )
    ).scalar_one_or_none()

    if existing_purchase:
        raise HTTPException(
            status_code=409,
            detail="Supplier invoice already exists"
        )

    calculated_subtotal = sum(item.quantity * item.unit_price for item in data.items)
    calculated_discount = sum(item.discount for item in data.items)
    calculated_tax = sum(item.tax for item in data.items)
    calculated_total = sum(item.line_total for item in data.items)

    if (
        abs(data.subtotal - calculated_subtotal) > 0.01
        or abs(data.discount - calculated_discount) > 0.01
        or abs(data.tax - calculated_tax) > 0.01
        or abs(data.total_amount - calculated_total) > 0.01
        or any(
            abs(item.line_total - (item.quantity * item.unit_price - item.discount + item.tax)) > 0.01
            for item in data.items
        )
    ):
        raise HTTPException(
            status_code=422,
            detail="Purchase totals do not match the submitted line items",
        )

    try:
        purchase = Purchase(
            supplier_id=data.supplier_id,
            purchase_date=data.purchase_date,
            supplier_invoice_no=data.supplier_invoice_no,
            subtotal=data.subtotal,
            discount=data.discount,
            tax=data.tax,
            total_amount=data.total_amount,
            status=data.status,
        )

        db.add(purchase)
        db.flush()

        purchase_items = []
        for item in data.items:
            product = db.get(Product, item.product_id)
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item.product_id} not found",
                )

            packaging = db.execute(
                select(ProductPackaging).where(
                    ProductPackaging.packaging_id == item.packaging_id,
                    ProductPackaging.product_id == item.product_id,
                )
            ).scalar_one_or_none()
            if not packaging:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Packaging {item.packaging_id} "
                        f"does not belong to product {item.product_id}"
                    ),
                )

            if item.received_quantity > item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Received quantity cannot exceed purchase quantity",
                )

            purchase_item = PurchaseItem(
                purchase_id=purchase.purchase_id,
                product_id=item.product_id,
                packaging_id=item.packaging_id,
                quantity=item.quantity,
                received_quantity=item.received_quantity,
                unit_price=item.unit_price,
                discount=item.discount,
                tax=item.tax,
                line_total=item.line_total,
            )
            db.add(purchase_item)
            purchase_items.append(purchase_item)

        db.flush()

        if purchase.status == "RECEIVED":
            for purchase_item in purchase_items:
                if purchase_item.received_quantity > 0:
                    create_purchase_movement(db, purchase_item, purchase_item.received_quantity)

        db.commit()
        db.refresh(purchase)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Purchase conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create purchase")

    return {
        "message": "Purchase created successfully",
        "purchase_id": purchase.purchase_id,
        "supplier_id": purchase.supplier_id,
        "supplier_invoice_no": purchase.supplier_invoice_no,
        "status": purchase.status
    }

@router.get("/", dependencies=[Depends(require_permission("purchases:read"))])
def get_purchases(
    from_date: date | None = Query(
        default=None,
        alias="from",
        description="Start date (YYYY-MM-DD)"
    ),
    to_date: date | None = Query(
        default=None,
        alias="to",
        description="End date (YYYY-MM-DD)"
    ),
    supplier_id: int | None = Query(
        default=None,
        description="Filter by supplier ID"
    ),
    status: str | None = Query(
        default=None,
        description="Filter by purchase status"
    ),
    db: Session = Depends(get_db)
):
    query = (
        select(Purchase)
        .options(
            joinedload(Purchase.supplier),
            joinedload(Purchase.items).joinedload(PurchaseItem.product),
            joinedload(Purchase.items).joinedload(PurchaseItem.packaging)
        )
        .order_by(Purchase.purchase_date.desc())
    )


    if from_date:
        query = query.where(Purchase.purchase_date >= from_date)

    if to_date:
        query = query.where(Purchase.purchase_date <= to_date)


    if supplier_id:
        query = query.where(Purchase.supplier_id == supplier_id)


    if status:
        query = query.where(Purchase.status == status.upper())

    purchases = db.execute(query).unique().scalars().all()

    return [
        {
            "purchase_id": purchase.purchase_id,
            "supplier_id": purchase.supplier_id,
            "supplier_name": (
                purchase.supplier.supplier_name
                if purchase.supplier else None
            ),
            "purchase_date": purchase.purchase_date,
            "supplier_invoice_no": purchase.supplier_invoice_no,
            "subtotal": float(purchase.subtotal),
            "discount": float(purchase.discount),
            "tax": float(purchase.tax),
            "total_amount": float(purchase.total_amount),
            "status": purchase.status,
            "items": [
                {
                    "purchase_item_id": item.purchase_item_id,
                    "product_id": item.product_id,
                    "product_name": (
                        item.product.product_name
                        if item.product else None
                    ),
                    "packaging_id": item.packaging_id,
                    "unit_name": (
                        item.packaging.unit_name
                        if item.packaging else None
                    ),
                    "quantity": float(item.quantity),
                    "received_quantity": float(item.received_quantity),
                    "unit_price": float(item.unit_price),
                    "discount": float(item.discount),
                    "tax": float(item.tax),
                    "line_total": float(item.line_total)
                }
                for item in purchase.items
            ]
        }
        for purchase in purchases
    ]
@router.get("/{purchase_id}", dependencies=[Depends(require_permission("purchases:read"))])
def get_purchase(
    purchase_id: int,
    db: Session = Depends(get_db)
):
    purchase = db.execute(
        select(Purchase)
        .options(
            joinedload(Purchase.supplier),
            joinedload(Purchase.items).joinedload(
                PurchaseItem.product
            ),
            joinedload(Purchase.items).joinedload(
                PurchaseItem.packaging
            )
        )
        .where(Purchase.purchase_id == purchase_id)
    ).unique().scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail=f"Purchase {purchase_id} not found"
        )

    return {
        "purchase_id": purchase.purchase_id,
        "supplier_id": purchase.supplier_id,
        "supplier_name": (
            purchase.supplier.supplier_name
            if purchase.supplier
            else None
        ),
        "purchase_date": purchase.purchase_date,
        "supplier_invoice_no": purchase.supplier_invoice_no,
        "subtotal": purchase.subtotal,
        "discount": purchase.discount,
        "tax": purchase.tax,
        "total_amount": purchase.total_amount,
        "status": purchase.status,
        "items": [
            {
                "purchase_item_id": item.purchase_item_id,
                "product_id": item.product_id,
                "product_name": (
                    item.product.product_name
                    if item.product
                    else None
                ),
                "packaging_id": item.packaging_id,
                "unit_name": (
                    item.packaging.unit_name
                    if item.packaging
                    else None
                ),
                "quantity": item.quantity,
                "received_quantity": item.received_quantity,
                "unit_price": item.unit_price,
                "discount": item.discount,
                "tax": item.tax,
                "line_total": item.line_total
            }
            for item in purchase.items
        ]
    }

@router.patch("/{purchase_id}/status", dependencies=[Depends(require_permission("purchases:write"))])
def update_purchase_status(
    purchase_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    purchase = db.get(Purchase, purchase_id)

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail=f"Purchase {purchase_id} not found"
        )

    new_status = data.get("status")

    allowed_status = ["PENDING", "RECEIVED", "CANCELLED"]

    if new_status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Status must be PENDING, RECEIVED or CANCELLED"
        )

    current_status = purchase.status


    if current_status in ["RECEIVED", "CANCELLED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Purchase cannot be updated from status {current_status}"
        )

    valid_transitions = {
        "PENDING": ["RECEIVED", "CANCELLED"],
        "PARTIALLY_RECEIVED": ["RECEIVED", "CANCELLED"],
    }

    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition: {current_status} → {new_status}"
        )

    try:

        if new_status == "RECEIVED":

            purchase_items = db.execute(
                select(PurchaseItem)
                .options(joinedload(PurchaseItem.packaging))
                .where(
                    PurchaseItem.purchase_id == purchase.purchase_id
                )
            ).scalars().all()

            for item in purchase_items:

                if item.packaging is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Packaging {item.packaging_id} not found for product {item.product_id}"
                    )

                remaining = float(item.quantity) - float(item.received_quantity)

                if remaining > 0:
                    create_purchase_movement(db, item, remaining)
                    item.received_quantity = item.quantity

            recalculate_purchase_status(purchase)

        else:
            purchase.status = new_status

        db.commit()
        db.refresh(purchase)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Purchase status update conflicts with existing data"
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update purchase status"
        )

    return {
        "message": "Purchase status updated successfully",
        "purchase_id": purchase.purchase_id,
        "status": purchase.status
    }


@router.patch("/{purchase_id}/receive", dependencies=[Depends(require_permission("purchases:write"))])
def receive_purchase_items(
    purchase_id: int,
    data: PurchaseReceive,
    db: Session = Depends(get_db)
):
    """
    Records a PARTIAL receiving event: some (not necessarily all) items,
    each for some (not necessarily the full remaining) quantity -- e.g.
    a supplier ships 3 of 5 ordered cartons today, the rest next week.

    Each call is additive: `quantity` in the request body is how much is
    arriving in THIS event, not the item's new total. Calling this
    multiple times over multiple shipments is exactly the intended use.
    """
    purchase = db.execute(
        select(Purchase)
        .options(joinedload(Purchase.items).joinedload(PurchaseItem.packaging))
        .where(Purchase.purchase_id == purchase_id)
    ).unique().scalar_one_or_none()

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail=f"Purchase {purchase_id} not found"
        )

    if purchase.status not in ("PENDING", "PARTIALLY_RECEIVED"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot receive items for a purchase in status {purchase.status}"
        )

    items_by_id = {item.purchase_item_id: item for item in purchase.items}

    try:
        for entry in data.items:
            item = items_by_id.get(entry.purchase_item_id)

            if item is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Purchase item {entry.purchase_item_id} not found on this purchase"
                )

            if item.packaging is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Packaging {item.packaging_id} not found for product {item.product_id}"
                )

            new_received = float(item.received_quantity) + float(entry.quantity)

            if new_received > float(item.quantity) + 0.0001:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Received quantity ({new_received}) would exceed "
                        f"ordered quantity ({item.quantity}) for product {item.product_id}"
                    )
                )

            create_purchase_movement(db, item, entry.quantity)
            item.received_quantity = new_received

        recalculate_purchase_status(purchase)

        db.commit()
        db.refresh(purchase)

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Receiving these items conflicts with existing data"
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to record received items"
        )

    return {
        "message": "Items received successfully",
        "purchase_id": purchase.purchase_id,
        "status": purchase.status,
        "items": [
            {
                "purchase_item_id": item.purchase_item_id,
                "received_quantity": item.received_quantity,
                "quantity": item.quantity,
            }
            for item in purchase.items
        ]
    }