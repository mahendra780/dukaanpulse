from fastapi import APIRouter, Depends, HTTPException,Body
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import require_permission
from app.db.database import get_db
from app.models.delivery import Delivery
from app.models.invoice import Invoice
from app.schemas.delivery import DeliveryCreate
from app.services.inventory_service import create_sale_movement


router = APIRouter(
    prefix="/deliveries",
    tags=["Deliveries"]
)


@router.post("/", status_code=201, dependencies=[Depends(require_permission("deliveries:write"))])
def create_delivery(
    data: DeliveryCreate,
    db: Session = Depends(get_db)
):
   
    invoice = db.execute(
        select(Invoice)
        .options(
            joinedload(Invoice.items)
        )
        .where(
            Invoice.invoice_id == data.invoice_id
        )
    ).unique().scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )


    existing_delivery = db.execute(
        select(Delivery).where(
            Delivery.invoice_id == data.invoice_id,
            Delivery.status != "CANCELLED"
        )
    ).scalar_one_or_none()

    if existing_delivery:
        raise HTTPException(
            status_code=409,
            detail="Delivery already exists for this invoice"
        )

    if existing_delivery:
        raise HTTPException(
            status_code=409,
            detail="Delivery already exists for this invoice"
        )

    delivery = Delivery(
        invoice_id=data.invoice_id,
        delivery_date=data.delivery_date,
        status=data.status,
        delivery_address=data.delivery_address,
        vehicle_number=data.vehicle_number,
        driver_name=data.driver_name,
        notes=data.notes
    )

    try:
        db.add(delivery)
        db.flush()

    
        if delivery.status == "DELIVERED":

            for invoice_item in invoice.items:
                create_sale_movement(
                    db,
                    invoice_item
                )

        db.commit()
        db.refresh(delivery)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Delivery conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create delivery")

    return {
        "message": "Delivery created successfully",
        "delivery_id": delivery.delivery_id,
        "invoice_id": delivery.invoice_id,
        "status": delivery.status
    }
@router.get("/", dependencies=[Depends(require_permission("deliveries:read"))])
def get_deliveries(
    db: Session = Depends(get_db)
):
    deliveries = db.execute(
        select(Delivery)
        .options(
            joinedload(Delivery.invoice)
        )
        .order_by(Delivery.delivery_id.desc())
    ).unique().scalars().all()

    result = []

    for delivery in deliveries:
        result.append({
            "delivery_id": delivery.delivery_id,
            "invoice_id": delivery.invoice_id,
            "invoice_number": (
                delivery.invoice.invoice_number
                if delivery.invoice
                else None
            ),
            "delivery_date": delivery.delivery_date,
            "status": delivery.status,
            "delivery_address": delivery.delivery_address,
            "vehicle_number": delivery.vehicle_number,
            "driver_name": delivery.driver_name,
            "notes": delivery.notes
        })

    return result

@router.patch("/{delivery_id}/status", dependencies=[Depends(require_permission("deliveries:write"))])
def update_delivery_status(
    delivery_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    delivery = db.execute(
        select(Delivery)
        .options(
            joinedload(Delivery.invoice)
            .joinedload(Invoice.items)
        )
        .where(Delivery.delivery_id == delivery_id)
    ).unique().scalar_one_or_none()

    if not delivery:
        raise HTTPException(
            status_code=404,
            detail=f"Delivery {delivery_id} not found"
        )

    new_status = data.get("status")

    allowed_status = [
        "PENDING",
        "DISPATCHED",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "FAILED",
        "CANCELLED"
    ]

    if new_status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail=(
                "Status must be PENDING, DISPATCHED, OUT_FOR_DELIVERY, "
                "DELIVERED, FAILED or CANCELLED"
            )
        )

    current_status = delivery.status

    if current_status in ["DELIVERED", "CANCELLED"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Delivery cannot be updated from status "
                f"{current_status}"
            )
        )

    valid_transitions = {
        "PENDING": ["DISPATCHED", "CANCELLED"],
        "DISPATCHED": ["OUT_FOR_DELIVERY", "FAILED", "CANCELLED"],
        "OUT_FOR_DELIVERY": ["DELIVERED", "FAILED", "CANCELLED"],
        "FAILED": ["OUT_FOR_DELIVERY", "CANCELLED"],
    }

    if new_status not in valid_transitions[current_status]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition: "
                f"{current_status} → {new_status}"
            )
        )

    delivery.status = new_status

    try:
        if new_status == "DELIVERED":
            for invoice_item in delivery.invoice.items:
                create_sale_movement(
                    db,
                    invoice_item
                )

        db.commit()
        db.refresh(delivery)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Delivery status update conflicts with existing data")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update delivery status")

    return {
        "message": "Delivery status updated successfully",
        "delivery_id": delivery.delivery_id,
        "status": delivery.status
    }