from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session,joinedload

from app.db.database import get_db
from app.models.purchase import Purchase, PurchaseItem
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.models.supplier import Supplier
from app.schemas.purchase import PurchaseCreate
from app.services.inventory_service import create_purchase_movement


router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"]
)


@router.post("/", status_code=201)
def create_purchase(
    data: PurchaseCreate,
    db: Session = Depends(get_db)
):
    # Check supplier
    supplier = db.get(Supplier, data.supplier_id)

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    # Check supplier invoice uniqueness
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

    purchase = Purchase(
        supplier_id=data.supplier_id,
        purchase_date=data.purchase_date,
        supplier_invoice_no=data.supplier_invoice_no,
        subtotal=data.subtotal,
        discount=data.discount,
        tax=data.tax,
        total_amount=data.total_amount,
        status=data.status
    )

    db.add(purchase)
    db.flush()

    for item in data.items:

        # Check product
        product = db.get(Product, item.product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Check packaging belongs to product
        packaging = db.execute(
            select(ProductPackaging).where(
                ProductPackaging.packaging_id == item.packaging_id,
                ProductPackaging.product_id == item.product_id
            )
        ).scalar_one_or_none()

        if not packaging:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Packaging {item.packaging_id} "
                    f"does not belong to product {item.product_id}"
                )
            )

        if item.received_quantity > item.quantity:
            raise HTTPException(
                status_code=400,
                detail="Received quantity cannot exceed purchase quantity"
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
            line_total=item.line_total
        )
    db.add(purchase_item)
    db.flush()

    if purchase.status == "RECEIVED":
        create_purchase_movement(
            db,
            purchase_item
        )

    db.commit()
    db.refresh(purchase)

    return {
        "message": "Purchase created successfully",
        "purchase_id": purchase.purchase_id,
        "supplier_id": purchase.supplier_id,
        "supplier_invoice_no": purchase.supplier_invoice_no,
        "status": purchase.status
    }

@router.get("/")
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

    # Date range filter
    if from_date:
        query = query.where(Purchase.purchase_date >= from_date)

    if to_date:
        query = query.where(Purchase.purchase_date <= to_date)

    # Supplier filter
    if supplier_id:
        query = query.where(Purchase.supplier_id == supplier_id)

    # Status filter
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
@router.get("/{purchase_id}")
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