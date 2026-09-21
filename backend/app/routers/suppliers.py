from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.supplier import Supplier
from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
    SupplierResponse,
)

router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"]
)


# ==========================================================
# GET ALL SUPPLIERS
# ==========================================================
@router.get("/", response_model=list[SupplierResponse])
def get_suppliers(db: Session = Depends(get_db)):
    result = db.execute(
        select(Supplier).order_by(Supplier.supplier_id)
    )
    return result.scalars().all()


# ==========================================================
# CREATE SUPPLIER
# ==========================================================
@router.post(
    "/",
    response_model=SupplierResponse,
    status_code=201,
)
def create_supplier(
    data: SupplierCreate,
    db: Session = Depends(get_db),
):
    try:
        supplier = Supplier(
            supplier_name=data.supplier_name,
            phone=data.phone,
            address=data.address,

            # Empty GST -> NULL
            gst_number=(
                data.gst_number.strip()
                if data.gst_number and data.gst_number.strip()
                else None
            ),

            payment_terms_days=data.payment_terms_days,
            status=data.status,
        )

        db.add(supplier)
        db.commit()
        db.refresh(supplier)

        return supplier

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Supplier GST number is invalid or already violates database constraints."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create supplier."
        )


# ==========================================================
# GET SINGLE SUPPLIER
# ==========================================================
@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
):
    supplier = db.get(Supplier, supplier_id)

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier {supplier_id} not found",
        )

    return supplier


# ==========================================================
# UPDATE SUPPLIER
# ==========================================================
@router.patch("/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    db: Session = Depends(get_db),
):
    supplier = db.get(Supplier, supplier_id)

    if not supplier:
        raise HTTPException(
            status_code=404,
            detail=f"Supplier {supplier_id} not found",
        )

    try:
        update_data = data.model_dump(exclude_unset=True)

        # Empty GST -> NULL (fixes chk_supplier_gst error)
        if "gst_number" in update_data:
            gst = update_data["gst_number"]
            update_data["gst_number"] = (
                gst.strip()
                if gst and gst.strip()
                else None
            )

        for field, value in update_data.items():
            setattr(supplier, field, value)

        db.commit()
        db.refresh(supplier)

        return {
            "message": "Supplier updated successfully",
            "supplier_id": supplier.supplier_id,
            "supplier_name": supplier.supplier_name,
            "status": supplier.status,
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Supplier GST number is invalid or violates database constraints."
        )

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to update supplier."
        )


