from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse


router = APIRouter(
    prefix="/categories",
    tags=["Categories"]
)


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("categories:write"))],
)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
):
    category = Category(
        category_name=data.category_name,
        status=data.status,
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with that name already exists.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create category right now. Please try again.",
        ) from exc

    return category


@router.get("/", dependencies=[Depends(require_permission("categories:read"))])
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
