import uuid
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.domain.inventory.models import InventoryBalance, InventoryLocation, MovementType, Product, StockMovement


def post_movement(
    data_product_id: uuid.UUID,
    data_location_id: uuid.UUID,
    data_quantity: Decimal,
    data_notes: str | None,
    kind: MovementType,
    principal: Principal,
    db: Session,
    direction: int = 1,
    reference: uuid.UUID | None = None,
) -> StockMovement:
    """Executes an inventory movement securely within the tenant boundary."""
    product = db.scalar(
        select(Product).where(Product.id == data_product_id, Product.organization_id == principal.organization_id)
    )
    location = db.scalar(
        select(InventoryLocation).where(
            InventoryLocation.id == data_location_id,
            InventoryLocation.organization_id == principal.organization_id,
            InventoryLocation.is_active == True,
        )
    )
    if not product or not location:
        raise HTTPException(404, "Product or active location not found")

    balance = db.scalar(
        select(InventoryBalance)
        .where(
            InventoryBalance.organization_id == principal.organization_id,
            InventoryBalance.product_id == product.id,
            InventoryBalance.location_id == location.id,
        )
        .with_for_update()
    )

    if not balance:
        balance = InventoryBalance(
            organization_id=principal.organization_id,
            product_id=product.id,
            location_id=location.id,
            available_quantity=0,
        )
        db.add(balance)
        db.flush()

    delta = data_quantity * direction
    if Decimal(str(balance.available_quantity)) + delta < 0:
        raise HTTPException(422, "Movement would create negative stock")

    balance.available_quantity = Decimal(str(balance.available_quantity)) + delta

    movement = StockMovement(
        organization_id=principal.organization_id,
        product_id=product.id,
        location_id=location.id,
        movement_type=kind,
        quantity_delta=delta,
        reference_id=reference,
        notes=data_notes,
        created_by=principal.user_id,
    )
    db.add(movement)
    db.flush()
    return movement
