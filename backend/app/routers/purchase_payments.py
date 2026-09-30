from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.purchase import Purchase
from app.models.purchase_payment import PurchasePayment
from app.schemas.purchase_payment import PurchasePaymentCreate

router = APIRouter(
    prefix="/purchase-payments",
    tags=["Purchase Payments"]
)


@router.post("/", status_code=201)
def create_purchase_payment(
    data: PurchasePaymentCreate,
    db: Session = Depends(get_db)
):

    purchase = db.get(
        Purchase,
        data.purchase_id
    )

    if not purchase:
        raise HTTPException(
            status_code=404,
            detail="Purchase not found"
        )
    db.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": data.purchase_id}
    )

    total_paid = db.execute(
        select(
            func.coalesce(
                func.sum(PurchasePayment.amount),
                0
            )
        ).where(
            PurchasePayment.purchase_id == data.purchase_id
        )
    ).scalar()

    remaining_amount = (
        float(purchase.total_amount)
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

    payment = PurchasePayment(
        purchase_id=data.purchase_id,
        payment_date=data.payment_date,
        amount=data.amount,
        payment_method=data.payment_method,
        reference_number=data.reference_number,
        notes=data.notes
    )

    try:
        db.add(payment)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Payment conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to record payment")

    return {
        "message": "Purchase payment recorded successfully",
        "purchase_payment_id": payment.purchase_payment_id,
        "purchase_id": payment.purchase_id,
        "paid_amount": payment.amount,
        "remaining_amount": remaining_amount - float(data.amount)
    }


@router.get("/")
def get_purchase_payments(
    db: Session = Depends(get_db)
):
    payments = db.execute(
        select(PurchasePayment)
        .options(
            joinedload(PurchasePayment.purchase).joinedload(Purchase.supplier)
        )
        .order_by(PurchasePayment.purchase_payment_id.desc())
    ).unique().scalars().all()

    result = []

    for payment in payments:
        result.append({
            "purchase_payment_id": payment.purchase_payment_id,
            "purchase_id": payment.purchase_id,
            "supplier_invoice_no": (
                payment.purchase.supplier_invoice_no
                if payment.purchase
                else None
            ),
            "supplier_name": (
                payment.purchase.supplier.supplier_name
                if payment.purchase and payment.purchase.supplier
                else None
            ),
            "payment_date": payment.payment_date,
            "amount": payment.amount,
            "payment_method": payment.payment_method,
            "reference_number": payment.reference_number,
            "notes": payment.notes
        })

    return result