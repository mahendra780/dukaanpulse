from fastapi import APIRouter, Depends, HTTPException,Body
from sqlalchemy import select
from sqlalchemy.orm import Session,joinedload


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
@router.get("/")
def get_orders(
    db: Session = Depends(get_db)
):
    orders = db.execute(
        select(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(
                OrderItem.product
            ),
            joinedload(Order.items).joinedload(
                OrderItem.packaging
            )
        )
        .order_by(Order.order_id.desc())
    ).unique().scalars().all()

    result = []

    for order in orders:
        result.append({
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "customer_name": (
                order.customer.customer_name
                if order.customer
                else None
            ),
            "order_date": order.order_date,
            "status": order.status,
            "notes": order.notes,
            "items": [
                {
                    "order_item_id": item.order_item_id,
                    "product_id": item.product_id,
                    "product_name": (
                        item.product.product_name
                        if item.product
                        else None
                    ),
                    "packaging_id": item.packaging_id,
                    "unit_name": (
                        item.packaging.unit_name
                        if item.packaging
                        else None
                    ),
                    "quantity": item.quantity
                }
                for item in order.items
            ]
        })

    return result

@router.get("/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.execute(
        select(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(
                OrderItem.product
            ),
            joinedload(Order.items).joinedload(
                OrderItem.packaging
            )
        )
        .where(Order.order_id == order_id)
    ).unique().scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found"
        )

    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "customer_name": (
            order.customer.customer_name
            if order.customer
            else None
        ),
        "order_date": order.order_date,
        "status": order.status,
        "notes": order.notes,
        "items": [
            {
                "order_item_id": item.order_item_id,
                "product_id": item.product_id,
                "product_name": (
                    item.product.product_name
                    if item.product
                    else None
                ),
                "packaging_id": item.packaging_id,
                "unit_name": (
                    item.packaging.unit_name
                    if item.packaging
                    else None
                ),
                "quantity": item.quantity
            }
            for item in order.items
        ]
    }

@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found"
        )

    # Check status in request
    new_status = data.get("status")

    allowed_status = [
        "PENDING",
        "CONFIRMED",
        "COMPLETED",
        "CANCELLED"
    ]

    if new_status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status must be PENDING, CONFIRMED, "
                "COMPLETED or CANCELLED"
            )
        )

    current_status = order.status

    # Prevent changing completed/cancelled orders
    if current_status in ["COMPLETED", "CANCELLED"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Order cannot be updated from status "
                f"{current_status}"
            )
        )

    # Allowed business transitions
    valid_transitions = {
        "PENDING": ["CONFIRMED", "CANCELLED"],
        "CONFIRMED": ["COMPLETED", "CANCELLED"]
    }

    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition: "
                f"{current_status} → {new_status}"
            )
        )

    order.status = new_status

    db.commit()
    db.refresh(order)

    return {
        "message": "Order status updated successfully",
        "order_id": order.order_id,
        "status": order.status
    }