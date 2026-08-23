from pydantic import BaseModel, Field, ConfigDict


class SupplierCreate(BaseModel):
    supplier_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    address: str
    gst_number: str | None = Field(default=None, max_length=15)
    payment_terms_days: int = Field(default=0, ge=0)


# ⭐ New Schema
class SupplierUpdate(BaseModel):
    supplier_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = None
    gst_number: str | None = Field(default=None, max_length=15)
    payment_terms_days: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class SupplierResponse(SupplierCreate):
    supplier_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)