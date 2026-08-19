from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session,joinedload

from app.db.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerResponse


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


@router.get("/", response_model=list[CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    result = db.execute(
        select(Customer)
        .order_by(Customer.customer_id)
    )

    return result.scalars().all()


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=201
)
def create_customer(
    data: CustomerCreate,
    db: Session = Depends(get_db)
):
    customer = Customer(
        customer_name=data.customer_name,
        phone=data.phone,
        address=data.address,
        area=data.area,
        credit_limit=data.credit_limit,
        payment_terms_days=data.payment_terms_days
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer
@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    customer = db.execute(
        select(Customer)
        .options(
            joinedload(Customer.orders)
        )
        .where(Customer.customer_id == customer_id)
    ).unique().scalar_one_or_none()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {customer_id} not found"
        )

    return {
        "customer_id": customer.customer_id,
        "customer_name": customer.customer_name,
        "phone": customer.phone,
        "address": customer.address,
        "area": customer.area,
        "credit_limit": float(customer.credit_limit),
        "payment_terms_days": customer.payment_terms_days,
        "status": customer.status,
        "orders": [
            {
                "order_id": order.order_id,
                "order_date": order.order_date,
                "status": order.status,
                "notes": order.notes
            }
            for order in customer.orders
        ]
    }