from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.payment import Payment


def recalculate_invoice_status(db: Session, invoice: Invoice) -> None:

    if invoice.status == "CANCELLED":
        return

    total_paid = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.invoice_id == invoice.invoice_id
        )
    ).scalar()

    total_paid = float(total_paid)
    total_amount = float(invoice.total_amount)

    if total_amount > 0 and total_paid >= total_amount:
        invoice.status = "PAID"
    elif total_paid > 0:
        invoice.status = "PARTIALLY_PAID"
    else:
        invoice.status = "UNPAID"