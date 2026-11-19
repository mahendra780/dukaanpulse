from app.models.purchase import Purchase


def recalculate_purchase_status(purchase: Purchase) -> None:

    if purchase.status == "CANCELLED":
        return

    items = purchase.items
    if not items:
        return

    if all(float(it.received_quantity) >= float(it.quantity) for it in items):
        purchase.status = "RECEIVED"
    elif any(float(it.received_quantity) > 0 for it in items):
        purchase.status = "PARTIALLY_RECEIVED"
    else:
        purchase.status = "PENDING"