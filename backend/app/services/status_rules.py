from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.product import Product
from app.models.supplier import Supplier

# Rule: an INACTIVE customer / supplier / product can't be used on a NEW
# order or purchase. Records that already exist are deliberately left
# alone (an order already in progress can still be confirmed, a purchase
# can still be received, payments can still be recorded) -- otherwise
# deactivating something would strand half-finished work.
#
# Each helper silently returns when the record doesn't exist at all, so
# the endpoint's own existing "not found" (404) handling stays in charge
# of that case.


def ensure_active_customer(db: Session, customer_id: int, context: str = "order") -> None:
    customer = db.get(Customer, customer_id)
    if customer is not None and customer.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=(
                f'Customer "{customer.customer_name}" is inactive, so a new {context} '
                f"can't be created for them. Reactivate the customer first."
            ),
        )


def ensure_active_supplier(db: Session, supplier_id: int, context: str = "purchase") -> None:
    supplier = db.get(Supplier, supplier_id)
    if supplier is not None and supplier.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=(
                f'Supplier "{supplier.supplier_name}" is inactive, so a new {context} '
                f"can't be created with them. Reactivate the supplier first."
            ),
        )


def ensure_active_products(db: Session, product_ids, context: str = "order") -> None:
    # dict.fromkeys de-duplicates while keeping order, so a product that
    # appears on several lines is only looked up once.
    for product_id in dict.fromkeys(product_ids):
        product = db.get(Product, product_id)
        if product is not None and product.status != "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail=(
                    f'Product "{product.product_name}" is inactive and can\'t be added '
                    f"to a new {context}. Reactivate the product first."
                ),
            )