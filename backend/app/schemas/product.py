from typing import Literal

from pydantic import BaseModel, Field


class ProductPackagingCreate(BaseModel):
    unit_name: str = Field(min_length=1, max_length=50)
    conversion_to_base: float = Field(gt=0)
    is_base_unit: bool = False
    is_purchase_unit: bool = False
    is_sale_unit: bool = False


class ProductCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=200)
    brand_name: str | None = Field(default=None, max_length=100)
    sku: str = Field(min_length=1, max_length=50)
    category_id: int
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"
    packaging: list[ProductPackagingCreate] = Field(min_length=1)


class ProductUpdate(BaseModel):
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    brand_name: str | None = Field(default=None, max_length=100)
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    category_id: int | None = None
    status: Literal["ACTIVE", "INACTIVE"] | None = None
