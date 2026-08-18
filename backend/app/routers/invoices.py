from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.schemas.invoice import InvoiceCreate


router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"]
)


@router.post("/", status_code=201)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db)
):
    # Check order
    order = db.get(Order, data.order_id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Prevent multiple invoices with same invoice number
    existing_invoice = db.execute(
        select(Invoice).where(
            Invoice.invoice_number == data.invoice_number
        )
    ).scalar_one_or_none()

    if existing_invoice:
        raise HTTPException(
            status_code=409,
            detail="Invoice number already exists"
        )

    # Basic order status validation
    if order.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cancelled order cannot be invoiced"
        )

    invoice = Invoice(
        order_id=data.order_id,
        invoice_number=data.invoice_number,
        invoice_date=data.invoice_date,
        subtotal=data.subtotal,
        discount=data.discount,
        tax=data.tax,
        total_amount=data.total_amount,
        status=data.status
    )

    db.add(invoice)
    db.flush()

    for item in data.items:

        product = db.get(Product, item.product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

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

        invoice_item = InvoiceItem(
            invoice_id=invoice.invoice_id,
            product_id=item.product_id,
            packaging_id=item.packaging_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount=item.discount,
            tax=item.tax,
            line_total=item.line_total
        )

        db.add(invoice_item)

    db.commit()
    db.refresh(invoice)

    return {
        "message": "Invoice created successfully",
        "invoice_id": invoice.invoice_id,
        "order_id": invoice.order_id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status
    }