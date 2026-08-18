from datetime import date
from pydantic import BaseModel, Field


class PurchaseItemCreate(BaseModel):
    product_id: int
    packaging_id: int
    quantity: float = Field(gt=0)
    received_quantity: float = Field(ge=0)
    unit_price: float = Field(ge=0)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    line_total: float = Field(ge=0)


class PurchaseCreate(BaseModel):
    supplier_id: int
    purchase_date: date
    supplier_invoice_no: str
    subtotal: float = Field(ge=0)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    total_amount: float = Field(ge=0)
    status: str = "PENDING"
    items: list[PurchaseItemCreate]