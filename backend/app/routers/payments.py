from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session,joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.services.invoice_service import recalculate_invoice_status

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post("/", status_code=201, dependencies=[Depends(require_permission("payments:write"))])
def create_payment(
    data: PaymentCreate,
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

    # Serialize concurrent payments against the same invoice so two
    # simultaneous payments can't both pass the "remaining amount" check.
    db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": data.invoice_id}
    )

    total_paid = db.execute(
        select(
            func.coalesce(
                func.sum(Payment.amount),
                0
            )
        ).where(
            Payment.invoice_id == data.invoice_id
        )
    ).scalar()

    remaining_amount = (
        float(invoice.total_amount)
        - float(total_paid)
    )

    if data.amount > remaining_amount:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Payment exceeds remaining amount. "
                f"Remaining: {remaining_amount}"
            )
        )

    payment = Payment(
        invoice_id=data.invoice_id,
        payment_date=data.payment_date,
        amount=data.amount,
        payment_method=data.payment_method,
        reference_number=data.reference_number,
        notes=data.notes
    )

    try:
        db.add(payment)
        db.flush()

        recalculate_invoice_status(db, invoice)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Payment conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to record payment")

    return {
        "message": "Payment recorded successfully",
        "payment_id": payment.payment_id,
        "invoice_id": payment.invoice_id,
        "paid_amount": payment.amount,
        "invoice_status": invoice.status
    }
@router.post("/apply-credit", dependencies=[Depends(require_permission("payments:write"))])
def apply_customer_credit(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Applies as much of the invoice's customer's existing credit_balance
    (built up from over-covering returns, see returns.py ->
    receive_return) as will fit against this invoice's remaining
    balance. Creates a normal Payment row (payment_method:
    CREDIT_APPLIED) so it's picked up by the same remaining/status
    logic as any other payment, and decrements the customer's
    credit_balance by the same amount -- this is the real wholesaler
    equivalent of "the refund we owed you now pays for this order"
    rather than a cash refund.
    """
    raw_invoice_id = data.get("invoice_id")

    if not raw_invoice_id:
        raise HTTPException(status_code=400, detail="invoice_id is required")

    try:
        # The frontend sends this as a plain JSON body (not a typed
        # Pydantic schema), so it can arrive as a string -- bind it as
        # an int explicitly, or Postgres rejects comparing bigint
        # invoice_id columns against a VARCHAR parameter.
        invoice_id = int(raw_invoice_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invoice_id must be a number")

    invoice = db.get(Invoice, invoice_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    order = db.get(Order, invoice.order_id)
    customer = db.get(Customer, order.customer_id) if order else None

    if customer is None:
        raise HTTPException(status_code=404, detail="Customer for this invoice not found")

    # Same advisory lock as a normal payment -- a concurrent payment or
    # another apply-credit call against this invoice/customer shouldn't
    # be able to double-spend the same credit or overshoot remaining.
    db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": invoice_id}
    )

    total_paid = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .where(Payment.invoice_id == invoice_id)
    ).scalar()

    remaining = max(0.0, float(invoice.total_amount) - float(total_paid))
    available_credit = float(customer.credit_balance)
    amount_to_apply = min(remaining, available_credit)

    if amount_to_apply <= 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Nothing to apply: "
                f"invoice remaining is {remaining}, customer credit balance is {available_credit}"
            )
        )

    payment = Payment(
        invoice_id=invoice_id,
        payment_date=invoice.invoice_date,
        amount=amount_to_apply,
        payment_method="CREDIT_APPLIED",
        reference_number=f"CREDIT-{customer.customer_id}",
        notes=f"Applied from customer #{customer.customer_id}'s credit balance",
    )

    try:
        db.add(payment)
        customer.credit_balance = available_credit - amount_to_apply
        db.flush()

        recalculate_invoice_status(db, invoice)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Applying credit conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to apply credit")

    return {
        "message": "Credit applied successfully",
        "invoice_id": invoice_id,
        "amount_applied": amount_to_apply,
        "remaining_customer_credit": customer.credit_balance,
        "invoice_status": invoice.status
    }


@router.get("/", dependencies=[Depends(require_permission("payments:read"))])
def get_payments(
    db: Session = Depends(get_db)
):
    payments = db.execute(
        select(Payment)
        .options(
            joinedload(Payment.invoice)
        )
        .order_by(Payment.payment_id.desc())
    ).unique().scalars().all()

    result = []

    for payment in payments:
        result.append({
            "payment_id": payment.payment_id,
            "invoice_id": payment.invoice_id,
            "invoice_number": (
                payment.invoice.invoice_number
                if payment.invoice
                else None
            ),
            "payment_date": payment.payment_date,
            "amount": payment.amount,
            "payment_method": payment.payment_method,
            "reference_number": payment.reference_number,
            "notes": payment.notes
        })

    return result