from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


def scoped_select(model: type[ModelT], workspace_id: int):
    return select(model).where(model.workspace_id == workspace_id)


def get_workspace_object(
    db: Session,
    model: type[ModelT],
    object_id: int,
    workspace_id: int,
    *,
    detail: str = "Record not found.",
) -> ModelT:
    primary_key = inspect(model).primary_key
    if len(primary_key) != 1:
        raise ValueError("Workspace lookup requires a single-column primary key.")
    instance = db.execute(
        scoped_select(model, workspace_id).where(primary_key[0] == object_id)
    ).scalar_one_or_none()
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return instance
