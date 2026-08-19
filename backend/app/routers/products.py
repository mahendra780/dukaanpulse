from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy import select,func
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.product import Product


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


@router.get("/")
def get_products(db: Session = Depends(get_db)):
    result = db.execute(
        select(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.packaging)
        )
        .order_by(Product.product_id)
    )

    products = result.scalars().unique().all()

    return [
        {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "brand_name": product.brand_name,
            "sku": product.sku,
            "status": product.status,
            "category": product.category.category_name,
            "packaging": [
                {
                    "packaging_id": packaging.packaging_id,
                    "unit_name": packaging.unit_name,
                    "conversion_to_base": float(
                        packaging.conversion_to_base
                    ),
                    "is_base_unit": packaging.is_base_unit,
                    "is_purchase_unit": packaging.is_purchase_unit,
                    "is_sale_unit": packaging.is_sale_unit
                }
                for packaging in product.packaging
            ]
        }
        for product in products
    ]