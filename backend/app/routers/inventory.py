from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.inventory import InventoryMovement
from app.models.product import Product
from app.models.packaging import ProductPackaging


router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)


@router.get("/stock/{product_id}")
def get_product_stock(
    product_id: int,
    db: Session = Depends(get_db)
):
    # Product check
    product = db.get(Product, product_id)

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # Calculate current stock
    result = db.execute(
        select(
            func.coalesce(
                func.sum(InventoryMovement.base_quantity),
                0
            )
        ).where(
            InventoryMovement.product_id == product_id
        )
    )

    current_stock = result.scalar()

    # Find base unit
    base_packaging = db.execute(
        select(ProductPackaging).where(
            ProductPackaging.product_id == product_id,
            ProductPackaging.is_base_unit == True
        )
    ).scalar_one_or_none()

    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "current_stock": float(current_stock),
        "base_unit": (
            base_packaging.unit_name
            if base_packaging
            else None
        )
    }