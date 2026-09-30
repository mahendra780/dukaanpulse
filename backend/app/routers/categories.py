from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.category import Category


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


@router.get("/")
def get_categories(db: Session = Depends(get_db)):
    result = db.execute(
        select(Category).order_by(Category.category_id)
    )

    categories = result.scalars().all()

    return [
        {
            "category_id": category.category_id,
            "category_name": category.category_name,
            "status": category.status
        }
        for category in categories
    ]