from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.permissions import require_permission
from app.db.database import get_db
from app.routers.auth import router as auth_router
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
from app.routers.purchase_payments import router as purchase_payments_router
from app.routers.returns import router as returns_router
from app.routers.users import router as users_router
from app.routers import dashboard
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(
    title="DukaanPulse API",
    description="Wholesale Distribution Analytics Platform",
    version="1.0.0",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(categories_router, dependencies=[Depends(get_current_user)])
app.include_router(products_router, dependencies=[Depends(get_current_user)])
app.include_router(customers_router, dependencies=[Depends(get_current_user)])
app.include_router(suppliers_router, dependencies=[Depends(get_current_user)])
app.include_router(purchases_router, dependencies=[Depends(get_current_user)])
app.include_router(inventory_router, dependencies=[Depends(get_current_user)])
app.include_router(orders_router, dependencies=[Depends(get_current_user)])
app.include_router(invoices_router, dependencies=[Depends(get_current_user)])
app.include_router(deliveries_router, dependencies=[Depends(get_current_user)])
app.include_router(payments_router, dependencies=[Depends(get_current_user)])
app.include_router(purchase_payments_router, dependencies=[Depends(get_current_user)])
app.include_router(returns_router, dependencies=[Depends(get_current_user)])
app.include_router(users_router, dependencies=[Depends(get_current_user)])
app.include_router(dashboard.router, dependencies=[Depends(get_current_user)])
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


@app.get("/health/db", dependencies=[Depends(require_permission("system:read"))])
def database_health(
    _current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(text("SELECT 1"))
    value = result.scalar()

    return {
        "database": "connected",
        "test": value
    }
