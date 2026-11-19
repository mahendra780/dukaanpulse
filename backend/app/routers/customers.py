from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session,joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse


router = APIRouter(
    prefix="/customers",
    tags=["Customers"]
)


@router.get("/", dependencies=[Depends(require_permission("customers:read"))])
def get_customers(
    search: str | None = Query(
        default=None,
        description="Search by customer name or phone"
    ),
    area: str | None = Query(
        default=None,
        description="Filter customers by area"
    ),
    db: Session = Depends(get_db)
):
    query = (
        select(Customer)
        .order_by(Customer.customer_id)
    )

    # Search by customer name or phone
    if search:
        keyword = f"%{search.strip()}%"
        query = query.where(
            or_(
                Customer.customer_name.ilike(keyword),
                Customer.phone.ilike(keyword)
            )
        )

    # Filter by area
    if area:
        query = query.where(
            Customer.area.ilike(area.strip())
        )

    customers = db.execute(query).scalars().all()

    return [
        {
            "customer_id": customer.customer_id,
            "customer_name": customer.customer_name,
            "phone": customer.phone,
            "address": customer.address,
            "area": customer.area,
            "credit_limit": float(customer.credit_limit),
            "credit_balance": float(customer.credit_balance),
            "payment_terms_days": customer.payment_terms_days,
            "status": customer.status
        }
        for customer in customers
    ]


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=201,
    dependencies=[Depends(require_permission("customers:write"))],
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
        payment_terms_days=data.payment_terms_days,
        status=data.status,
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Customer conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create customer")

    return customer
@router.get("/{customer_id}", dependencies=[Depends(require_permission("customers:read"))])
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
        "credit_balance": float(customer.credit_balance),
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
@router.patch("/{customer_id}", dependencies=[Depends(require_permission("customers:write"))])
def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    db: Session = Depends(get_db)
):
    customer = db.get(Customer, customer_id)

    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {customer_id} not found"
        )

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(customer, field, value)

    try:
        db.commit()
        db.refresh(customer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Customer update conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update customer")

    return {
        "message": "Customer updated successfully",
        "customer_id": customer.customer_id,
        "customer_name": customer.customer_name,
        "status": customer.status
    }