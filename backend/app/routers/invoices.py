from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, OrderItem
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
    order = db.execute(
        select(Order)
        .options(joinedload(Order.items))
        .where(Order.order_id == data.order_id)
    ).unique().scalar_one_or_none()

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

    submitted_order_items = sorted(
        (item.product_id, item.packaging_id, item.quantity) for item in data.items
    )
    order_items = sorted(
        (item.product_id, item.packaging_id, float(item.quantity))
        for item in order.items
    )
    if submitted_order_items != order_items:
        raise HTTPException(
            status_code=422,
            detail="Invoice items must match the selected order items",
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
            detail="Invoice totals do not match the submitted line items",
        )

    try:
        invoice = Invoice(
            order_id=data.order_id,
            invoice_number=data.invoice_number,
            invoice_date=data.invoice_date,
            subtotal=data.subtotal,
            discount=data.discount,
            tax=data.tax,
            total_amount=data.total_amount,
            status=data.status,
        )

        db.add(invoice)
        db.flush()

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

            db.add(
                InvoiceItem(
                    invoice_id=invoice.invoice_id,
                    product_id=item.product_id,
                    packaging_id=item.packaging_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                    tax=item.tax,
                    line_total=item.line_total,
                )
            )

        db.commit()
        db.refresh(invoice)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Invoice conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create invoice")

    return {
        "message": "Invoice created successfully",
        "invoice_id": invoice.invoice_id,
        "order_id": invoice.order_id,
        "invoice_number": invoice.invoice_number,
        "status": invoice.status
    }

@router.get("/")
def get_invoices(
    db: Session = Depends(get_db)
):
    invoices = db.execute(
        select(Invoice)
        .options(
            joinedload(Invoice.order),
            joinedload(Invoice.items).joinedload(
                InvoiceItem.product
            ),
            joinedload(Invoice.items).joinedload(
                InvoiceItem.packaging
            )
        )
        .order_by(Invoice.invoice_id.desc())
    ).unique().scalars().all()

    result = []

    for invoice in invoices:
        result.append({
            "invoice_id": invoice.invoice_id,
            "order_id": invoice.order_id,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "subtotal": invoice.subtotal,
            "discount": invoice.discount,
            "tax": invoice.tax,
            "total_amount": invoice.total_amount,
            "status": invoice.status,
            "items": [
                {
                    "invoice_item_id": item.invoice_item_id,
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
                    "unit_price": item.unit_price,
                    "discount": item.discount,
                    "tax": item.tax,
                    "line_total": item.line_total
                }
                for item in invoice.items
            ]
        })

    return result
@router.get("/{invoice_id}")
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    invoice = db.execute(
        select(Invoice)
        .options(
            joinedload(Invoice.order),
            joinedload(Invoice.items).joinedload(
                InvoiceItem.product
            ),
            joinedload(Invoice.items).joinedload(
                InvoiceItem.packaging
            ),
            joinedload(Invoice.payments),
            joinedload(Invoice.delivery),
            joinedload(Invoice.returns)
        )
        .where(Invoice.invoice_id == invoice_id)
    ).unique().scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_id} not found"
        )

    return {
        "invoice_id": invoice.invoice_id,
        "order_id": invoice.order_id,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "subtotal": invoice.subtotal,
        "discount": invoice.discount,
        "tax": invoice.tax,
        "total_amount": invoice.total_amount,
        "status": invoice.status,

        "items": [
            {
                "invoice_item_id": item.invoice_item_id,
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
                "unit_price": item.unit_price,
                "discount": item.discount,
                "tax": item.tax,
                "line_total": item.line_total
            }
            for item in invoice.items
        ],

        "payments": [
            {
                "payment_id": payment.payment_id,
                "payment_date": payment.payment_date,
                "amount": payment.amount,
                "payment_method": payment.payment_method,
                "reference_number": payment.reference_number,
                "notes": payment.notes
            }
            for payment in invoice.payments
        ],

        "delivery": (
            {
                "delivery_id": invoice.delivery.delivery_id,
                "delivery_date": invoice.delivery.delivery_date,
                "status": invoice.delivery.status,
                "delivery_address": invoice.delivery.delivery_address,
                "vehicle_number": invoice.delivery.vehicle_number,
                "driver_name": invoice.delivery.driver_name,
                "notes": invoice.delivery.notes
            }
            if invoice.delivery
            else None
        ),

        "returns": [
            {
                "return_id": return_record.return_id,
                "return_date": return_record.return_date,
                "reason": return_record.reason,
                "status": return_record.status,
                "notes": return_record.notes
            }
            for return_record in invoice.returns
        ]
    }
