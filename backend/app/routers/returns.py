from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session,joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.models.payment import Payment
from app.models.returns import Return, ReturnItem
from app.schemas.returns import ReturnCreate
from app.services.return_service import get_returned_quantities


router = APIRouter(
    prefix="/returns",
    tags=["Returns"]
)


@router.post("/", status_code=201, dependencies=[Depends(require_permission("returns:write"))])
def create_return(
    data: ReturnCreate,
    db: Session = Depends(get_db)
):

    invoice = db.get(
        Invoice,
        data.invoice_id
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )
    if invoice.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cancelled invoice cannot be returned"
        )


    invoiced_items = db.execute(
        select(InvoiceItem).where(InvoiceItem.invoice_id == data.invoice_id)
    ).scalars().all()

    invoiced_qty_by_key = {}
    for inv_item in invoiced_items:
        key = (inv_item.product_id, inv_item.packaging_id)
        invoiced_qty_by_key[key] = invoiced_qty_by_key.get(key, 0) + float(inv_item.quantity)

    already_returned = get_returned_quantities(db, data.invoice_id)

    for item in data.items:
        key = (item.product_id, item.packaging_id)
        sold_qty = invoiced_qty_by_key.get(key)

        if sold_qty is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Product {item.product_id} (packaging {item.packaging_id}) "
                    f"was not sold on this invoice"
                )
            )

        returned_so_far = already_returned.get(key, 0)
        returnable = sold_qty - returned_so_far

        if item.quantity > returnable + 0.0001:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Cannot return {item.quantity} of product {item.product_id}: "
                    f"only {returnable} is returnable ({sold_qty} sold, "
                    f"{returned_so_far} already returned/requested on this invoice)"
                )
            )

    return_record = Return(
        invoice_id=data.invoice_id,
        return_date=data.return_date,
        reason=data.reason,
        status=data.status,
        notes=data.notes
    )

    try:
        db.add(return_record)
        db.flush()

        for item in data.items:

            product = db.get(
                Product,
                item.product_id
            )

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item.product_id} not found"
                )

            packaging = db.execute(
                select(ProductPackaging).where(
                    ProductPackaging.packaging_id
                    == item.packaging_id,
                    ProductPackaging.product_id
                    == item.product_id
                )
            ).scalar_one_or_none()

            if not packaging:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Packaging {item.packaging_id} "
                        f"does not belong to product "
                        f"{item.product_id}"
                    )
                )

            return_item = ReturnItem(
                return_id=return_record.return_id,
                product_id=item.product_id,
                packaging_id=item.packaging_id,
                quantity=item.quantity,
                condition=item.condition
            )

            db.add(return_item)

        db.commit()
        db.refresh(return_record)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Return conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create return")

    return {
        "message": "Return created successfully",
        "return_id": return_record.return_id,
        "invoice_id": return_record.invoice_id,
        "status": return_record.status
    }

@router.patch("/{return_id}/approve", dependencies=[Depends(require_permission("returns:approve"))])
def approve_return(
    return_id: int,
    db: Session = Depends(get_db)
):
    return_record = db.get(
        Return,
        return_id
    )

    if not return_record:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != "REQUESTED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Return cannot be approved "
                f"from status {return_record.status}"
            )
        )

    return_record.status = "APPROVED"

    db.commit()
    db.refresh(return_record)

    return {
        "message": "Return approved successfully",
        "return_id": return_record.return_id,
        "status": return_record.status
    }
@router.patch("/{return_id}/receive", dependencies=[Depends(require_permission("returns:receive"))])
def receive_return(
    return_id: int,
    db: Session = Depends(get_db)
):
    from app.services.inventory_service import create_return_movement
    from app.services.invoice_service import recalculate_invoice_status

    return_record = db.get(
        Return,
        return_id
    )

    if not return_record:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Return cannot be received "
                f"from status {return_record.status}"
            )
        )

    return_record.status = "RECEIVED"

    try:
        invoice = db.get(Invoice, return_record.invoice_id)

        total_credit = 0.0

        for return_item in return_record.items:
            create_return_movement(
                db,
                return_item
            )

            invoice_item = db.execute(
                select(InvoiceItem).where(
                    InvoiceItem.invoice_id == return_record.invoice_id,
                    InvoiceItem.product_id == return_item.product_id,
                    InvoiceItem.packaging_id == return_item.packaging_id,
                )
            ).scalars().first()

            if invoice_item:
                total_credit += (
                    float(return_item.quantity)
                    * float(invoice_item.unit_price)
                )

        credit_applied_to_invoice = 0.0
        credit_added_to_customer_balance = 0.0

        if total_credit > 0 and invoice is not None:
            paid_so_far = db.execute(
                select(func.coalesce(func.sum(Payment.amount), 0))
                .where(Payment.invoice_id == return_record.invoice_id)
            ).scalar()

            remaining_before = max(0.0, float(invoice.total_amount) - float(paid_so_far))
            credit_applied_to_invoice = min(total_credit, remaining_before)
            credit_added_to_customer_balance = total_credit - credit_applied_to_invoice

            if credit_applied_to_invoice > 0:
                db.add(
                    Payment(
                        invoice_id=return_record.invoice_id,
                        payment_date=return_record.return_date,
                        amount=credit_applied_to_invoice,
                        payment_method="RETURN_CREDIT",
                        reference_number=f"RETURN-{return_record.return_id}",
                        notes=f"Auto-generated credit for return #{return_record.return_id}",
                    )
                )

            if credit_added_to_customer_balance > 0:
                order = db.get(Order, invoice.order_id)
                customer = db.get(Customer, order.customer_id) if order else None
                if customer is not None:
                    customer.credit_balance = float(customer.credit_balance) + credit_added_to_customer_balance

            db.flush()

        if invoice is not None:
            recalculate_invoice_status(db, invoice)

        db.commit()
        db.refresh(return_record)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Return receipt conflicts with existing data: {getattr(e, 'orig', e)}"
        )
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to receive return")

    return {
        "message": "Return received successfully",
        "return_id": return_record.return_id,
        "status": return_record.status,
        "credit_applied": total_credit,
        "credit_applied_to_invoice": credit_applied_to_invoice,
        "credit_added_to_customer_balance": credit_added_to_customer_balance,
        "invoice_status": invoice.status if invoice is not None else None
    }

@router.get("/", dependencies=[Depends(require_permission("returns:read"))])
def get_returns(
    db: Session = Depends(get_db)
):
    returns = db.execute(
        select(Return)
        .options(
            joinedload(Return.invoice),
            joinedload(Return.items).joinedload(
                ReturnItem.product
            ),
            joinedload(Return.items).joinedload(
                ReturnItem.packaging
            )
        )
        .order_by(Return.return_id.desc())
    ).unique().scalars().all()

    result = []

    for return_record in returns:
        result.append({
            "return_id": return_record.return_id,
            "invoice_id": return_record.invoice_id,
            "invoice_number": (
                return_record.invoice.invoice_number
                if return_record.invoice
                else None
            ),
            "return_date": return_record.return_date,
            "reason": return_record.reason,
            "status": return_record.status,
            "notes": return_record.notes,
            "items": [
                {
                    "return_item_id": item.return_item_id,
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
                    "condition": item.condition
                }
                for item in return_record.items
            ]
        })

    return result
@router.get("/{return_id}", dependencies=[Depends(require_permission("returns:read"))])
def get_return(
    return_id: int,
    db: Session = Depends(get_db)
):
    return_record = db.execute(
        select(Return)
        .options(
            joinedload(Return.invoice),
            joinedload(Return.items).joinedload(
                ReturnItem.product
            ),
            joinedload(Return.items).joinedload(
                ReturnItem.packaging
            )
        )
        .where(Return.return_id == return_id)
    ).unique().scalar_one_or_none()

    if not return_record:
        raise HTTPException(
            status_code=404,
            detail=f"Return {return_id} not found"
        )

    return {
        "return_id": return_record.return_id,
        "invoice_id": return_record.invoice_id,
        "invoice_number": (
            return_record.invoice.invoice_number
            if return_record.invoice
            else None
        ),
        "return_date": return_record.return_date,
        "reason": return_record.reason,
        "status": return_record.status,
        "notes": return_record.notes,
        "items": [
            {
                "return_item_id": item.return_item_id,
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
                "condition": item.condition
            }
            for item in return_record.items
        ]
    }