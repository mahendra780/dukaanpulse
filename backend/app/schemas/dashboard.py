from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    total_products: int
    total_customers: int
    total_suppliers: int
    total_orders: int

    total_sales: float
    total_purchases: float

    current_inventory_items: float

    model_config = ConfigDict(from_attributes=True)