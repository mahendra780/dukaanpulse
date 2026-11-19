from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order


def get_invoiced_quantities(db: Session, order_id: int) -> dict:
    rows = db.execute(
        select(InvoiceItem.product_id, InvoiceItem.packaging_id, InvoiceItem.quantity)
        .join(Invoice, Invoice.invoice_id == InvoiceItem.invoice_id)
        .where(Invoice.order_id == order_id, Invoice.status != "CANCELLED")
    ).all()

    totals = {}
    for product_id, packaging_id, quantity in rows:
        key = (product_id, packaging_id)
        totals[key] = totals.get(key, 0) + float(quantity)
    return totals


def recalculate_order_status(db: Session, order: Order) -> None:

    if order.status == "CANCELLED":
        return

    invoiced = get_invoiced_quantities(db, order.order_id)

    all_full = True
    any_invoiced = False

    for item in order.items:
        key = (item.product_id, item.packaging_id)
        done = invoiced.get(key, 0)
        if done > 0:
            any_invoiced = True
        if done < float(item.quantity) - 0.0001:
            all_full = False

    if all_full:
        order.status = "COMPLETED"
    elif any_invoiced:
        order.status = "PARTIALLY_FULFILLED"
    else:
        order.status = "CONFIRMED"