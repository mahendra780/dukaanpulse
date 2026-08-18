from datetime import date

from pydantic import BaseModel


class DeliveryCreate(BaseModel):
    invoice_id: int
    delivery_date: date | None = None
    status: str = "PENDING"
    delivery_address: str
    vehicle_number: str | None = None
    driver_name: str | None = None
    notes: str | None = None