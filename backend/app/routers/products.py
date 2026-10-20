from fastapi import APIRouter, Depends, HTTPException, Query
from app.models.category import Category
from sqlalchemy import select, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.packaging import ProductPackaging
from app.models.product import Product
from app.models.inventory import InventoryMovement
from app.schemas.product import ProductCreate, ProductUpdate


router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


@router.get("/", dependencies=[Depends(require_permission("products:read"))])
def get_products(
    search: str | None = Query(
        default=None,
        description="Search by product name, brand or SKU"
    ),
    db: Session = Depends(get_db)
):
    query = (
        select(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.packaging)
        )
        .order_by(Product.product_id)
    )
    if search:
        keyword = f"%{search.strip()}%"
        query = query.where(
            or_(
                Product.product_name.ilike(keyword),
                Product.brand_name.ilike(keyword),
                Product.sku.ilike(keyword)
            )
        )

    products = db.execute(query).unique().scalars().all()

    result = []

    for product in products:

        current_stock = db.scalar(
            select(
                func.coalesce(
                    func.sum(InventoryMovement.base_quantity),
                    0
                )
            ).where(
                InventoryMovement.product_id == product.product_id
            )
        )

        result.append({
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
                    p.unit_name
                    for p in product.packaging
                    if p.is_base_unit
                ),
                None
            ),
            "packaging": [
                {
                    "packaging_id": p.packaging_id,
                    "unit_name": p.unit_name,
                    "conversion_to_base": float(
                        p.conversion_to_base
                    ),
                    "is_base_unit": p.is_base_unit,
                    "is_purchase_unit": p.is_purchase_unit,
                    "is_sale_unit": p.is_sale_unit
                }
                for p in product.packaging
            ]
        })

    return result


@router.post("/", status_code=201, dependencies=[Depends(require_permission("products:write"))])
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db)
):
    category = db.get(Category, data.category_id)
    if not category:
        raise HTTPException(
            status_code=404,
            detail=f"Category {data.category_id} not found"
        )

    existing = db.execute(
        select(Product).where(Product.sku == data.sku)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="SKU already exists"
        )

    if sum(packaging.is_base_unit for packaging in data.packaging) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one packaging unit must be the base unit"
        )

    try:
        product = Product(
            product_name=data.product_name,
            brand_name=data.brand_name,
            sku=data.sku,
            category_id=data.category_id,
            status=data.status
        )
        db.add(product)
        db.flush()

        for packaging in data.packaging:
            db.add(ProductPackaging(
                product_id=product.product_id,
                unit_name=packaging.unit_name,
                conversion_to_base=packaging.conversion_to_base,
                is_base_unit=packaging.is_base_unit,
                is_purchase_unit=packaging.is_purchase_unit,
                is_sale_unit=packaging.is_sale_unit
            ))

        db.commit()
        db.refresh(product)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create product"
        )

    return {
        "message": "Product created successfully",
        "product_id": product.product_id,
        "product_name": product.product_name
    }


@router.get("/{product_id}", dependencies=[Depends(require_permission("products:read"))])
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
@router.patch("/{product_id}", dependencies=[Depends(require_permission("products:write"))])
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = db.get(Product, product_id)

    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found"
        )

    allowed_fields = {
        "product_name",
        "brand_name",
        "category_id",
        "sku",
        "status"
    }

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided for update"
        )


    if "category_id" in update_data:
        category = db.get(Category, update_data["category_id"])
        if not category:
            raise HTTPException(
                status_code=404,
                detail=f"Category {update_data['category_id']} not found"
            )

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
    if "status" in update_data:
        if update_data["status"] not in ["ACTIVE", "INACTIVE"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be ACTIVE or INACTIVE"
            )
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