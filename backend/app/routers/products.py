from fastapi import APIRouter, Depends,HTTPException,Body
from app.models.category import Category
from sqlalchemy import select,func
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.product import Product
from app.models.inventory import InventoryMovement


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
@router.get("/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.execute(
        select(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.packaging)
        )
        .where(Product.product_id == product_id)
    ).unique().scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found"
        )

    current_stock = db.execute(
        select(
            func.coalesce(
                func.sum(InventoryMovement.base_quantity),
                0
            )
        ).where(
            InventoryMovement.product_id == product_id
        )
    ).scalar()

    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "brand_name": product.brand_name,
        "sku": product.sku,
        "status": product.status,
        "category": (
            product.category.category_name
            if product.category
            else None
        ),
        "current_stock": float(current_stock),
        "base_unit": next(
            (
                packaging.unit_name
                for packaging in product.packaging
                if packaging.is_base_unit
            ),
            None
        ),
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
@router.patch("/{product_id}")
def update_product(
    product_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    product = db.get(Product, product_id)

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found"
        )

    # Allowed fields only
    allowed_fields = {
        "product_name",
        "brand_name",
        "category_id",
        "sku",
        "status"
    }

    update_data = {
        key: value
        for key, value in data.items()
        if key in allowed_fields
    }

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided for update"
        )

    # Validate category
    if "category_id" in update_data:
        category = db.get(Category, update_data["category_id"])
        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"Category {update_data['category_id']} not found"
            )

    # Validate duplicate SKU
    if "sku" in update_data:
        existing = db.execute(
            select(Product).where(
                Product.sku == update_data["sku"],
                Product.product_id != product_id
            )
        ).scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=409,
                detail="SKU already exists"
            )

    # Validate status
    if "status" in update_data:
        if update_data["status"] not in ["ACTIVE", "INACTIVE"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be ACTIVE or INACTIVE"
            )

    # Update fields
    for field, value in update_data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)

    return {
        "message": "Product updated successfully",
        "product_id": product.product_id,
        "product_name": product.product_name,
        "status": product.status
    }