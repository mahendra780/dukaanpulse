from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, extract
from sqlalchemy.orm import Session
from datetime import date
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
@router.get("/sales")
def get_sales_dashboard(
    year: int = Query(..., description="Year (Example: 2026)"),
    db: Session = Depends(get_db)
):
    sales = db.execute(
        select(
            extract("month", Invoice.invoice_date).label("month"),
            func.coalesce(
                func.sum(Invoice.total_amount),
                0
            ).label("sales")
        )
        .where(
            extract("year", Invoice.invoice_date) == year
        )
        .group_by(
            extract("month", Invoice.invoice_date)
        )
        .order_by(
            extract("month", Invoice.invoice_date)
        )
    ).all()

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar",
        4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep",
        10: "Oct", 11: "Nov", 12: "Dec"
    }

    result = []

    sales_map = {
        int(row.month): float(row.sales)
        for row in sales
    }

    for month in range(1, 13):
        result.append({
            "month": month_names[month],
            "sales": sales_map.get(month, 0.0)
        })

    return result


@router.get("/sales/daily")
def get_daily_sales(
    sales_date: date = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    total_sales = db.scalar(
        select(
            func.coalesce(
                func.sum(Invoice.total_amount),
                0
            )
        ).where(
            Invoice.invoice_date == sales_date
        )
    )

    invoice_count = db.scalar(
        select(func.count(Invoice.invoice_id))
        .where(Invoice.invoice_date == sales_date)
    )

    invoices = db.execute(
        select(Invoice)
        .where(Invoice.invoice_date == sales_date)
        .order_by(Invoice.invoice_id)
    ).scalars().all()

    return {
        "date": sales_date,
        "invoice_count": invoice_count,
        "total_sales": float(total_sales),
        "invoices": [
            {
                "invoice_id": invoice.invoice_id,
                "invoice_number": invoice.invoice_number,
                "total_amount": float(invoice.total_amount),
                "status": invoice.status
            }
            for invoice in invoices
        ]
    }
@router.get("/purchases")
def get_purchase_dashboard(
    year: int = Query(..., description="Year (Example: 2026)"),
    db: Session = Depends(get_db)
):
    purchases = db.execute(
        select(
            extract("month", Purchase.purchase_date).label("month"),
            func.coalesce(
                func.sum(Purchase.total_amount),
                0
            ).label("purchase")
        )
        .where(
            extract("year", Purchase.purchase_date) == year
        )
        .group_by(
            extract("month", Purchase.purchase_date)
        )
        .order_by(
            extract("month", Purchase.purchase_date)
        )
    ).all()

    month_names = {
        1: "Jan", 2: "Feb", 3: "Mar",
        4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep",
        10: "Oct", 11: "Nov", 12: "Dec"
    }

    purchase_map = {
        int(row.month): float(row.purchase)
        for row in purchases
    }

    result = []

    for month in range(1, 13):
        result.append({
            "month": month_names[month],
            "purchase": purchase_map.get(month, 0.0)
        })

    return result