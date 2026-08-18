from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierResponse


router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"]
)


@router.get("/", response_model=list[SupplierResponse])
def get_suppliers(db: Session = Depends(get_db)):
    result = db.execute(
        select(Supplier)
        .order_by(Supplier.supplier_id)
    )

    return result.scalars().all()


@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=201
)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db)
):
    supplier = Supplier(
        supplier_name=data.supplier_name,
        phone=data.phone,
        address=data.address,
        gst_number=data.gst_number,
        payment_terms_days=data.payment_terms_days
    )

    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    return supplier