from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate

router = APIRouter(
    prefix="/payments",
    tags=["Payments"]
)


@router.post("/", status_code=201)
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

    db.add(payment)
    db.flush()

    new_total_paid = (
        float(total_paid)
        + float(data.amount)
    )

    if new_total_paid == float(invoice.total_amount):
        invoice.status = "PAID"

    elif new_total_paid > 0:
        invoice.status = "PARTIALLY_PAID"

    else:
        invoice.status = "UNPAID"

    db.commit()

    return {
        "message": "Payment recorded successfully",
        "payment_id": payment.payment_id,
        "invoice_id": payment.invoice_id,
        "paid_amount": payment.amount,
        "invoice_status": invoice.status
    }