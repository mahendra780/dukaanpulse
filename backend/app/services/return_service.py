from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.returns import Return, ReturnItem


def get_returned_quantities(db: Session, invoice_id: int) -> dict:

    rows = db.execute(
        select(ReturnItem.product_id, ReturnItem.packaging_id, ReturnItem.quantity)
        .join(Return, Return.return_id == ReturnItem.return_id)
        .where(
            Return.invoice_id == invoice_id,
            Return.status.notin_(["REJECTED", "CANCELLED"])
        )
    ).all()

    totals = {}
    for product_id, packaging_id, quantity in rows:
        key = (product_id, packaging_id)
        totals[key] = totals.get(key, 0) + float(quantity)
    return totals