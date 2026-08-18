from datetime import date

from pydantic import BaseModel, Field


class InvoiceItemCreate(BaseModel):
    product_id: int
    packaging_id: int
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    line_total: float = Field(ge=0)


class InvoiceCreate(BaseModel):
    order_id: int
    invoice_number: str = Field(min_length=1, max_length=100)
    invoice_date: date
    subtotal: float = Field(ge=0)
    discount: float = Field(default=0, ge=0)
    tax: float = Field(default=0, ge=0)
    total_amount: float = Field(ge=0)
    status: str = "UNPAID"
    items: list[InvoiceItemCreate] = Field(min_length=1)