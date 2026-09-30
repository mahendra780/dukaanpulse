from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session,joinedload

from app.db.database import get_db
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.services.invoice_service import recalculate_invoice_status

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
@router.get("/")
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