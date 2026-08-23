from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate,SupplierUpdate ,SupplierResponse


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
@router.patch("/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    db: Session = Depends(get_db)
):
    supplier = db.get(Supplier, supplier_id)

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier {supplier_id} not found"
        )

    # Update only provided fields
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)

    return {
        "message": "Supplier updated successfully",
        "supplier_id": supplier.supplier_id,
        "supplier_name": supplier.supplier_name,
        "status": supplier.status
    }