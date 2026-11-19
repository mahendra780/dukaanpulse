from datetime import date

from pydantic import BaseModel, Field


class PurchasePaymentCreate(BaseModel):
    purchase_id: int
    payment_date: date
    amount: float = Field(gt=0)
    payment_method: str
    reference_number: str | None = None
    notes: str | None = None