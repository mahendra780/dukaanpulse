from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.packaging import ProductPackaging
from app.models.returns import Return, ReturnItem
from app.schemas.returns import ReturnCreate


router = APIRouter(
    prefix="/returns",
    tags=["Returns"]
)


@router.post("/", status_code=201)
def create_return(
    data: ReturnCreate,
    db: Session = Depends(get_db)
):
    # 1. Check invoice
    invoice = db.get(
        Invoice,
        data.invoice_id
    )

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    # 2. Cancelled invoice cannot be returned
    if invoice.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Cancelled invoice cannot be returned"
        )

    # 3. Create return
    return_record = Return(
        invoice_id=data.invoice_id,
        return_date=data.return_date,
        reason=data.reason,
        status=data.status,
        notes=data.notes
    )

    db.add(return_record)
    db.flush()

    # 4. Create return items
    for item in data.items:

        # Check product
        product = db.get(
            Product,
            item.product_id
        )

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {item.product_id} not found"
            )

        # Check product + packaging relationship
        packaging = db.execute(
            select(ProductPackaging).where(
                ProductPackaging.packaging_id
                == item.packaging_id,
                ProductPackaging.product_id
                == item.product_id
            )
        ).scalar_one_or_none()

        if not packaging:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Packaging {item.packaging_id} "
                    f"does not belong to product "
                    f"{item.product_id}"
                )
            )

        return_item = ReturnItem(
            return_id=return_record.return_id,
            product_id=item.product_id,
            packaging_id=item.packaging_id,
            quantity=item.quantity,
            condition=item.condition
        )

        db.add(return_item)

    db.commit()
    db.refresh(return_record)

    return {
        "message": "Return created successfully",
        "return_id": return_record.return_id,
        "invoice_id": return_record.invoice_id,
        "status": return_record.status
    }

@router.patch("/{return_id}/approve")
def approve_return(
    return_id: int,
    db: Session = Depends(get_db)
):
    return_record = db.get(
        Return,
        return_id
    )

    if not return_record:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != "REQUESTED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Return cannot be approved "
                f"from status {return_record.status}"
            )
        )

    return_record.status = "APPROVED"

    db.commit()
    db.refresh(return_record)

    return {
        "message": "Return approved successfully",
        "return_id": return_record.return_id,
        "status": return_record.status
    }
@router.patch("/{return_id}/receive")
def receive_return(
    return_id: int,
    db: Session = Depends(get_db)
):
    from app.services.inventory_service import create_return_movement

    return_record = db.get(
        Return,
        return_id
    )

    if not return_record:
        raise HTTPException(
            status_code=404,
            detail="Return not found"
        )

    if return_record.status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Return cannot be received "
                f"from status {return_record.status}"
            )
        )

    return_record.status = "RECEIVED"

    # Create inventory movement for each returned item
    for return_item in return_record.items:
        create_return_movement(
            db,
            return_item
        )

    db.commit()
    db.refresh(return_record)

    return {
        "message": "Return received successfully",
        "return_id": return_record.return_id,
        "status": return_record.status
    }