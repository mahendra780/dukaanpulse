from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.delivery import Delivery
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.schemas.invoice import InvoiceCreate
from app.services.order_service import get_invoiced_quantities, recalculate_order_status
from app.services.return_service import get_returned_quantities


router = APIRouter(
    prefix="/invoices",
    tags=["Invoices"]
)


@router.post("/", status_code=201, dependencies=[Depends(require_permission("invoices:write"))])
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

    # Only a confirmed order (or one already partially invoiced) can be
    # invoiced. This used to be unenforced here -- the frontend only
    # offered CONFIRMED orders in its picker, but the API itself let a
    # PENDING or COMPLETED order be invoiced directly.
    if order.status not in ("CONFIRMED", "PARTIALLY_FULFILLED"):
        raise HTTPException(
            status_code=400,
            detail=f"Order must be CONFIRMED or PARTIALLY_FULFILLED to be invoiced (current status: {order.status})",
        )

    # Each submitted line just needs to belong to this order and not
    # exceed what's left to invoice on that line -- NOT match the
    # order's full quantity exactly. This is what makes partial
    # invoicing (and therefore PARTIALLY_FULFILLED) possible: one order
    # can now be covered by more than one invoice over time.
    already_invoiced = get_invoiced_quantities(db, order.order_id)
    order_items_by_key = {
        (item.product_id, item.packaging_id): float(item.quantity)
        for item in order.items
    }

    for item in data.items:
        key = (item.product_id, item.packaging_id)
        ordered_qty = order_items_by_key.get(key)

        if ordered_qty is None:
            raise HTTPException(
                status_code=422,
                detail=f"Product {item.product_id} (packaging {item.packaging_id}) is not on this order",
            )

        already = already_invoiced.get(key, 0)
        new_total = already + float(item.quantity)

        if new_total > ordered_qty + 0.0001:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invoicing {item.quantity} of product {item.product_id} would exceed "
                    f"the ordered quantity ({ordered_qty}); {already} already invoiced on other invoices"
                ),
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

        db.flush()

        # Now that this invoice's items are flushed, get_invoiced_quantities
        # (used inside recalculate_order_status) will see them when it
        # re-sums invoiced quantity per order line.
        recalculate_order_status(db, order)

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


@router.patch("/{invoice_id}/status", dependencies=[Depends(require_permission("invoices:write"))])
def cancel_invoice(
    invoice_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    The only supported transition here is -> CANCELLED, and only from
    UNPAID. This exists specifically for "this invoice shouldn't have
    been created this way" (e.g. invoiced more than was actually in
    stock, wrong order picked) -- NOT for unwinding a paid sale, which
    is a refund question this endpoint deliberately doesn't attempt to
    answer. Cancelling frees the invoiced quantity back onto the order
    (see recalculate_order_status) so a corrected invoice can be made.
    """
    new_status = data.get("status")

    if new_status != "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="This endpoint only supports cancelling an invoice (status: CANCELLED)"
        )

    invoice = db.get(Invoice, invoice_id)

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_id} not found"
        )

    if invoice.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Invoice is already cancelled"
        )

    if invoice.status != "UNPAID":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Only an UNPAID invoice can be cancelled directly (current status: "
                f"{invoice.status}). A paid or partially paid invoice needs the payment "
                f"handled first -- cancelling it here would silently lose track of money "
                f"already received."
            )
        )

    active_delivery = db.execute(
        select(Delivery).where(
            Delivery.invoice_id == invoice_id,
            Delivery.status != "CANCELLED"
        )
    ).scalar_one_or_none()

    if active_delivery:
        raise HTTPException(
            status_code=400,
            detail=(
                f"This invoice has an active delivery (status: {active_delivery.status}). "
                f"Cancel that delivery first."
            )
        )

    try:
        invoice.status = "CANCELLED"
        db.flush()

        order = db.get(Order, invoice.order_id)
        if order is not None:
            recalculate_order_status(db, order)

        db.commit()
        db.refresh(invoice)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to cancel invoice")

    return {
        "message": "Invoice cancelled successfully",
        "invoice_id": invoice.invoice_id,
        "status": invoice.status,
        "order_status": order.status if order is not None else None
    }


@router.get("/", dependencies=[Depends(require_permission("invoices:read"))])
def get_invoices(
    db: Session = Depends(get_db)
):
    invoices = db.execute(
        select(Invoice)
        .options(
            joinedload(Invoice.order).joinedload(Order.customer),
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
        customer = invoice.order.customer if invoice.order else None

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
            # Used by the Deliveries page to auto-fill the delivery
            # address when an invoice is selected.
            "customer_name": customer.customer_name if customer else None,
            "customer_address": customer.address if customer else None,
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
@router.get("/{invoice_id}", dependencies=[Depends(require_permission("invoices:read"))])
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    invoice = db.execute(
        select(Invoice)
        .options(
            joinedload(Invoice.order).joinedload(Order.customer),
            joinedload(Invoice.items).joinedload(
                InvoiceItem.product
            ),
            joinedload(Invoice.items).joinedload(
                InvoiceItem.packaging
            ),
            joinedload(Invoice.payments),
            joinedload(Invoice.deliveries),
            joinedload(Invoice.returns)
        )
        .where(Invoice.invoice_id == invoice_id)
    ).unique().scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice {invoice_id} not found"
        )

    returned = get_returned_quantities(db, invoice_id)
    customer = invoice.order.customer if invoice.order else None

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

        "customer_id": customer.customer_id if customer else None,
        "customer_name": customer.customer_name if customer else None,
        "customer_credit_balance": float(customer.credit_balance) if customer else 0,

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
                "line_total": item.line_total,
                # How much of this line is still eligible for a
                # return -- sold quantity minus whatever's already
                # been claimed by a non-rejected/cancelled return.
                "returned_quantity": returned.get((item.product_id, item.packaging_id), 0),
                "returnable_quantity": float(item.quantity) - returned.get((item.product_id, item.packaging_id), 0),
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

        # A cancelled delivery attempt doesn't block a fresh one for
        # the same invoice (see deliveries.py), so an invoice can now
        # have more than one delivery row over time. "delivery" here
        # is whichever one is still active (not cancelled) -- that's
        # the one that actually matters for "is this order on its way".
        # Every attempt, including cancelled ones, is in "deliveries".
        "delivery": next(
            (
                {
                    "delivery_id": d.delivery_id,
                    "delivery_date": d.delivery_date,
                    "status": d.status,
                    "delivery_address": d.delivery_address,
                    "vehicle_number": d.vehicle_number,
                    "driver_name": d.driver_name,
                    "notes": d.notes
                }
                for d in invoice.deliveries
                if d.status != "CANCELLED"
            ),
            None
        ),

        "deliveries": [
            {
                "delivery_id": d.delivery_id,
                "delivery_date": d.delivery_date,
                "status": d.status,
                "delivery_address": d.delivery_address,
                "vehicle_number": d.vehicle_number,
                "driver_name": d.driver_name,
                "notes": d.notes
            }
            for d in invoice.deliveries
        ],

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