from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.schemas.order import OrderCreate


router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.post("/", status_code=201)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db)
):
    # Check customer
    customer = db.get(Customer, data.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    order = Order(
        customer_id=data.customer_id,
        order_date=data.order_date,
        status=data.status,
        notes=data.notes
    )

    db.add(order)
    db.flush()

    for item in data.items:

        # Check product
        product = db.get(Product, item.product_id)

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Check packaging belongs to product
        packaging = db.execute(
            select(ProductPackaging).where(
                ProductPackaging.packaging_id == item.packaging_id,
                ProductPackaging.product_id == item.product_id
            )
        ).scalar_one_or_none()

        if not packaging:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Packaging {item.packaging_id} "
                    f"does not belong to product {item.product_id}"
                )
            )

        order_item = OrderItem(
            order_id=order.order_id,
            product_id=item.product_id,
            packaging_id=item.packaging_id,
            quantity=item.quantity
        )

        db.add(order_item)

    db.commit()
    db.refresh(order)

    return {
        "message": "Order created successfully",
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "status": order.status
    }