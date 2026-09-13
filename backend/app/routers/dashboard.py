from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.database import get_db

from app.models.product import Product
from app.models.customer import Customer
from app.models.supplier import Supplier
from app.models.order import Order
from app.models.invoice import Invoice
from app.models.purchase import Purchase
from app.models.inventory import InventoryMovement

from app.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse
)
def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    # ---------- COUNT QUERIES ----------

    total_products = db.scalar(
        select(func.count(Product.product_id))
    )

    total_customers = db.scalar(
        select(func.count(Customer.customer_id))
    )

    total_suppliers = db.scalar(
        select(func.count(Supplier.supplier_id))
    )

    total_orders = db.scalar(
        select(func.count(Order.order_id))
    )

    # ---------- SUM QUERIES ----------

    total_sales = db.scalar(
        select(
            func.coalesce(
                func.sum(Invoice.total_amount),
                0
            )
        )
    )

    total_purchases = db.scalar(
        select(
            func.coalesce(
                func.sum(Purchase.total_amount),
                0
            )
        )
    )

    current_inventory_items = db.scalar(
        select(
            func.coalesce(
                func.sum(
                    InventoryMovement.base_quantity
                ),
                0
            )
        )
    )

    return DashboardSummaryResponse(
        total_products=total_products,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        total_orders=total_orders,
        total_sales=float(total_sales),
        total_purchases=float(total_purchases),
        current_inventory_items=float(
            current_inventory_items
        )
    )