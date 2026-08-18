from datetime import date

from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    product_id: int
    packaging_id: int
    quantity: float = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    order_date: date
    status: str = "PENDING"
    notes: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)