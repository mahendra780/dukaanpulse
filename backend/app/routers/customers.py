from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

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