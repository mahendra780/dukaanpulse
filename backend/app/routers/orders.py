from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.schemas.order import OrderCreate
from app.services.order_service import get_invoiced_quantities
from app.services.status_rules import ensure_active_customer, ensure_active_products
router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.post("/", status_code=201, dependencies=[Depends(require_permission("orders:write"))])
def create_order(
    
    data: OrderCreate,
    db: Session = Depends(get_db)
):
    ensure_active_customer(db, data.customer_id, "order")
    ensure_active_products(db, [item.product_id for item in data.items], "order")
    customer = db.get(Customer, data.customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    try:
        order = Order(
            customer_id=data.customer_id,
            order_date=data.order_date,
            status=data.status,
            notes=data.notes,
        )

        db.add(order)
        db.flush()

        for item in data.items:
            product = db.get(Product, item.product_id)
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item.product_id} not found",
                )

            packaging = db.execute(
                select(ProductPackaging).where(
                    ProductPackaging.packaging_id == item.packaging_id,
                    ProductPackaging.product_id == item.product_id,
                )
            ).scalar_one_or_none()
            if not packaging:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Packaging {item.packaging_id} "
                        f"does not belong to product {item.product_id}"
                    ),
                )

            db.add(
                OrderItem(
                    order_id=order.order_id,
                    product_id=item.product_id,
                    packaging_id=item.packaging_id,
                    quantity=item.quantity,
                )
            )

        db.commit()
        db.refresh(order)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create order")

    return {
        "message": "Order created successfully",
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "status": order.status
    }

@router.get("/", dependencies=[Depends(require_permission("orders:read"))])
def get_orders(
    status: str | None = Query(
        default=None,
        description="Filter by order status"
    ),
    search: str | None = Query(
        default=None,
        description="Search by customer name"
    ),
    db: Session = Depends(get_db)
):
    invoice_totals = (
        select(
            Invoice.order_id.label("order_id"),
            func.sum(Invoice.total_amount).label("total_amount"),
        )
        .group_by(Invoice.order_id)
        .subquery()
    )
    query = (
        select(Order, invoice_totals.c.total_amount)
        .outerjoin(invoice_totals, invoice_totals.c.order_id == Order.order_id)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.items).joinedload(OrderItem.packaging)
        )
        .order_by(Order.order_id.desc())
    )


    if status:
        query = query.where(Order.status == status.upper())


    if search:
        keyword = f"%{search.strip()}%"
        query = (
            query.join(Customer)
            .where(Customer.customer_name.ilike(keyword))
        )

    rows = db.execute(query).unique().all()

    result = []

    for order, invoice_total in rows:

        invoiced = get_invoiced_quantities(db, order.order_id)

        result.append({
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "customer_name": (
                order.customer.customer_name
                if order.customer else None
            ),
            "order_date": order.order_date,
            "status": order.status,
            "notes": order.notes,


            "total_amount": float(invoice_total or 0),

            "items": [
                {
                    "order_item_id": item.order_item_id,
                    "product_id": item.product_id,
                    "product_name": (
                        item.product.product_name
                        if item.product else None
                    ),
                    "packaging_id": item.packaging_id,
                    "unit_name": (
                        item.packaging.unit_name
                        if item.packaging else None
                    ),
                    "quantity": float(item.quantity),
                    "invoiced_quantity": invoiced.get((item.product_id, item.packaging_id), 0),
                    "remaining_quantity": float(item.quantity) - invoiced.get((item.product_id, item.packaging_id), 0),
                }
                for item in order.items
            ]
        })

    return result



@router.get("/{order_id}", dependencies=[Depends(require_permission("orders:read"))])
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    invoice_totals = (
        select(
            Invoice.order_id.label("order_id"),
            func.sum(Invoice.total_amount).label("total_amount"),
        )
        .group_by(Invoice.order_id)
        .subquery()
    )
    row = db.execute(
        select(Order, invoice_totals.c.total_amount)
        .outerjoin(invoice_totals, invoice_totals.c.order_id == Order.order_id)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.items).joinedload(OrderItem.packaging)
        )
        .where(Order.order_id == order_id)
    ).unique().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"Order {order_id} not found"
        )

    order, invoice_total = row

    invoiced = get_invoiced_quantities(db, order.order_id)

    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "customer_name": (
            order.customer.customer_name
            if order.customer else None
        ),
        "order_date": order.order_date,
        "status": order.status,
        "notes": order.notes,
        "total_amount": float(invoice_total or 0),
        "items": [
            {
                "order_item_id": item.order_item_id,
                "product_id": item.product_id,
                "product_name": (
                    item.product.product_name
                    if item.product else None
                ),
                "packaging_id": item.packaging_id,
                "unit_name": (
                    item.packaging.unit_name
                    if item.packaging else None
                ),
                "quantity": float(item.quantity),
                "invoiced_quantity": invoiced.get((item.product_id, item.packaging_id), 0),
                "remaining_quantity": float(item.quantity) - invoiced.get((item.product_id, item.packaging_id), 0),
            }
            for item in order.items
        ]
    }
@router.patch("/{order_id}/status", dependencies=[Depends(require_permission("orders:write"))])
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
            detail="Status must be PENDING, CONFIRMED, COMPLETED or CANCELLED"
        )

    current_status = order.status

    if current_status in ["COMPLETED", "CANCELLED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be updated from status {current_status}"
        )

    valid_transitions = {
        "PENDING": ["CONFIRMED", "CANCELLED"],
        "CONFIRMED": ["COMPLETED", "CANCELLED"],
        "PARTIALLY_FULFILLED": ["COMPLETED", "CANCELLED"],
    }

    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition: {current_status} → {new_status}"
        )

    order.status = new_status

    db.commit()
    db.refresh(order)

    return {
        "message": "Order status updated successfully",
        "order_id": order.order_id,
        "status": order.status
    }