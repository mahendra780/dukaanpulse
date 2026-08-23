from pydantic import BaseModel, Field, ConfigDict


class CustomerCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    address: str
    area: str = Field(max_length=100)
    credit_limit: float = Field(default=0, ge=0)
    payment_terms_days: int = Field(default=0, ge=0)


# ⭐ New Schema
class CustomerUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = None
    area: str | None = Field(default=None, max_length=100)
    credit_limit: float | None = Field(default=None, ge=0)
    payment_terms_days: int | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class CustomerResponse(CustomerCreate):
    customer_id: int
    status: str

    model_config = ConfigDict(from_attributes=True)