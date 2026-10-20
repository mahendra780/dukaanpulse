from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    category_name: str = Field(min_length=1, max_length=100)
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"


class CategoryResponse(CategoryCreate):
    category_id: int

    model_config = ConfigDict(from_attributes=True)
