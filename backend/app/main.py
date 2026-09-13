from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.routers.categories import router as categories_router
from app.routers.products import router as products_router
from app.routers.customers import router as customers_router
from app.routers.suppliers import router as suppliers_router
from app.routers.purchases import router as purchases_router
from app.routers.inventory import router as inventory_router
from app.routers.orders import router as orders_router
from app.routers.invoices import router as invoices_router
from app.routers.deliveries import router as deliveries_router
from app.routers.payments import router as payments_router
from app.routers.returns import router as returns_router
from app.routers import dashboard
app = FastAPI(
    title="DukaanPulse API",
    description="Wholesale Distribution Analytics Platform",
    version="1.0.0"
)


app.include_router(categories_router)
app.include_router(products_router)
app.include_router(customers_router)
app.include_router(suppliers_router)
app.include_router(purchases_router)
app.include_router(inventory_router)
app.include_router(orders_router)
app.include_router(invoices_router)
app.include_router(deliveries_router)
app.include_router(payments_router)
app.include_router(returns_router)
app.include_router(dashboard.router)
@app.get("/")
def root():
    return {
        "message": "DukaanPulse API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    value = result.scalar()

    return {
        "database": "connected",
        "test": value
    }