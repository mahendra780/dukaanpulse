from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ReturnItemCreate(BaseModel):
    product_id: int
    packaging_id: int
    quantity: float = Field(gt=0)
    condition: Literal[
        "RESELLABLE",
        "DAMAGED",
        "EXPIRED",
        "SUPPLIER_RETURN",
    ]


class ReturnCreate(BaseModel):
    invoice_id: int
    return_date: date
    reason: Literal[
        "DAMAGED",
        "EXPIRED",
        "WRONG_PRODUCT",
        "QUALITY_ISSUE",
        "EXCESS_QUANTITY",
        "OTHER",
    ]
    status: Literal[
        "REQUESTED",
        "APPROVED",
        "RECEIVED",
        "REJECTED",
        "CANCELLED",
    ] = "REQUESTED"
    notes: str | None = None
    items: list[ReturnItemCreate] = Field(min_length=1)