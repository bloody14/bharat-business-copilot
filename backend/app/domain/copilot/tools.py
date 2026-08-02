from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from app.domain.inventory.models import Product, StockMovement, InventoryBalance
from decimal import Decimal

def get_inventory_summary(db: Session, org_id: str) -> dict[str, Any]:
    """Returns a high-level summary of the inventory."""
    items = db.scalars(select(Product).where(Product.organization_id == org_id)).all()
    
    balances = dict(db.execute(
        select(InventoryBalance.product_id, func.coalesce(func.sum(InventoryBalance.available_quantity), 0))
        .where(InventoryBalance.organization_id == org_id)
        .group_by(InventoryBalance.product_id)
    ).all())
    
    total_qty = Decimal("0")
    low_stock = 0
    out_of_stock = 0
    
    for item in items:
        qty = Decimal(str(balances.get(item.id, 0)))
        total_qty += qty
        
        if qty <= 0:
            out_of_stock += 1
        elif qty <= Decimal(str(item.reorder_level)):
            low_stock += 1

    return {
        "total_products": len(items),
        "total_stock_quantity": str(total_qty),
        "low_stock_products_count": low_stock,
        "out_of_stock_products_count": out_of_stock
    }

def lookup_product(db: Session, org_id: str, query: str) -> list[dict[str, Any]]:
    """Looks up products by name or SKU and returns their details and current stock."""
    # Enforce safe limits
    items = db.scalars(
        select(Product).where(
            Product.organization_id == org_id,
            or_(
                Product.name.ilike(f"%{query}%"),
                Product.sku.ilike(f"%{query}%")
            )
        ).limit(5)
    ).all()
    
    results = []
    for item in items:
        qty = db.scalar(
            select(func.coalesce(func.sum(InventoryBalance.available_quantity), 0))
            .where(
                InventoryBalance.organization_id == org_id,
                InventoryBalance.product_id == item.id
            )
        ) or 0
        
        results.append({
            "name": item.name,
            "sku": item.sku,
            "unit": item.unit.value,
            "cost_price": str(item.cost_price),
            "selling_price": str(item.selling_price),
            "gst_rate": str(item.gst_rate),
            "reorder_level": str(item.reorder_level),
            "available_quantity": str(qty)
        })
    return results

def get_low_stock_products(db: Session, org_id: str) -> list[dict[str, Any]]:
    """Returns products that are at or below their reorder level."""
    items = db.scalars(select(Product).where(Product.organization_id == org_id)).all()
    
    balances = dict(db.execute(
        select(InventoryBalance.product_id, func.coalesce(func.sum(InventoryBalance.available_quantity), 0))
        .where(InventoryBalance.organization_id == org_id)
        .group_by(InventoryBalance.product_id)
    ).all())
    
    results = []
    for item in items:
        qty = Decimal(str(balances.get(item.id, 0)))
        if qty <= Decimal(str(item.reorder_level)):
            results.append({
                "name": item.name,
                "sku": item.sku,
                "available_quantity": str(qty),
                "reorder_level": str(item.reorder_level),
                "status": "out_of_stock" if qty <= 0 else "low_stock"
            })
            if len(results) >= 20: # hard limit
                break
    return results

def get_recent_movements(db: Session, org_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Returns the most recent stock movements (receipts, adjustments, transfers)."""
    limit = min(max(1, limit), 20)
    movements = db.scalars(
        select(StockMovement)
        .where(StockMovement.organization_id == org_id)
        .order_by(StockMovement.occurred_at.desc())
        .limit(limit)
    ).all()
    
    results = []
    for m in movements:
        product = db.scalar(select(Product.name).where(Product.id == m.product_id, Product.organization_id == org_id))
        results.append({
            "product_name": product or "Unknown Product",
            "type": m.movement_type.value,
            "quantity_delta": str(m.quantity_delta),
            "occurred_at": m.occurred_at.isoformat(),
            "notes": m.notes
        })
    return results

def get_product_movements(db: Session, org_id: str, product_sku: str, limit: int = 5) -> list[dict[str, Any]]:
    """Returns the movement history for a specific product SKU."""
    limit = min(max(1, limit), 10)
    product = db.scalar(select(Product).where(Product.organization_id == org_id, Product.sku == product_sku))
    if not product:
        return []
        
    movements = db.scalars(
        select(StockMovement)
        .where(StockMovement.organization_id == org_id, StockMovement.product_id == product.id)
        .order_by(StockMovement.occurred_at.desc())
        .limit(limit)
    ).all()
    
    results = []
    for m in movements:
        results.append({
            "type": m.movement_type.value,
            "quantity_delta": str(m.quantity_delta),
            "occurred_at": m.occurred_at.isoformat(),
            "notes": m.notes
        })
    return results

import datetime
import uuid
from app.core.auth import Principal
from app.domain.inventory.models import InventoryLocation
from app.domain.copilot.models import CopilotActionProposal

def _resolve_product(db: Session, org_id: str, query: str) -> Product | None:
    return db.scalar(
        select(Product).where(
            Product.organization_id == org_id,
            Product.is_active == True,
            or_(Product.name.ilike(f"%{query}%"), Product.sku.ilike(f"%{query}%"))
        )
    )

def _resolve_location(db: Session, org_id: str, query: str) -> InventoryLocation | None:
    return db.scalar(
        select(InventoryLocation).where(
            InventoryLocation.organization_id == org_id,
            InventoryLocation.is_active == True,
            InventoryLocation.name.ilike(f"%{query}%")
        )
    )

def _check_permission(principal: Principal) -> str | None:
    if principal.role not in {"owner", "admin", "manager", "inventory"}:
        return "Permission denied. You do not have inventory write permissions."
    return None

def _create_proposal(db: Session, principal: Principal, action_type: str, payload: dict, display_title: str, display_subtitle: str, display_quantity: str) -> dict:
    proposal = CopilotActionProposal(
        organization_id=principal.organization_id,
        action_type=action_type,
        payload=payload,
        expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10),
        created_by=principal.user_id
    )
    db.add(proposal)
    db.flush()
    
    return {
        "_is_action_proposal": True,
        "proposal": {
            "action_id": str(proposal.id),
            "action_type": proposal.action_type,
            "status": proposal.status,
            "expires_at": proposal.expires_at.isoformat(),
            "payload": proposal.payload,
            "display_title": display_title,
            "display_subtitle": display_subtitle,
            "display_quantity": display_quantity
        }
    }

def prepare_stock_receipt(db: Session, principal: Principal, product_query: str, location_query: str, quantity: float) -> dict[str, Any]:
    """Prepares a stock receipt action for user confirmation."""
    err = _check_permission(principal)
    if err: return {"error": err}
    if quantity <= 0: return {"error": "Quantity must be greater than zero."}
    
    product = _resolve_product(db, principal.organization_id, product_query)
    location = _resolve_location(db, principal.organization_id, location_query)
    if not product: return {"error": f"Product '{product_query}' not found."}
    if not location: return {"error": f"Location '{location_query}' not found."}
    
    payload = {"product_id": str(product.id), "location_id": str(location.id), "quantity": quantity, "notes": "Prepared by Copilot"}
    
    return _create_proposal(db, principal, "receipt", payload, 
                            display_title=f"Stock Inward: {product.name}",
                            display_subtitle=f"Location: {location.name}",
                            display_quantity=f"+{quantity} {product.unit.value}")

def prepare_stock_adjustment(db: Session, principal: Principal, product_query: str, location_query: str, quantity: float) -> dict[str, Any]:
    """Prepares a stock adjustment action for user confirmation. Quantity can be negative."""
    err = _check_permission(principal)
    if err: return {"error": err}
    if quantity == 0: return {"error": "Quantity must not be zero."}
    
    product = _resolve_product(db, principal.organization_id, product_query)
    location = _resolve_location(db, principal.organization_id, location_query)
    if not product: return {"error": f"Product '{product_query}' not found."}
    if not location: return {"error": f"Location '{location_query}' not found."}
    
    payload = {"product_id": str(product.id), "location_id": str(location.id), "quantity": quantity, "notes": "Prepared by Copilot"}
    sign = "+" if quantity > 0 else ""
    
    return _create_proposal(db, principal, "adjustment", payload, 
                            display_title=f"Stock Adjustment: {product.name}",
                            display_subtitle=f"Location: {location.name}",
                            display_quantity=f"{sign}{quantity} {product.unit.value}")

def prepare_stock_transfer(db: Session, principal: Principal, product_query: str, source_location_query: str, destination_location_query: str, quantity: float) -> dict[str, Any]:
    """Prepares a stock transfer action for user confirmation."""
    err = _check_permission(principal)
    if err: return {"error": err}
    if quantity <= 0: return {"error": "Quantity must be greater than zero."}
    
    product = _resolve_product(db, principal.organization_id, product_query)
    src_loc = _resolve_location(db, principal.organization_id, source_location_query)
    dest_loc = _resolve_location(db, principal.organization_id, destination_location_query)
    if not product: return {"error": f"Product '{product_query}' not found."}
    if not src_loc: return {"error": f"Source location '{source_location_query}' not found."}
    if not dest_loc: return {"error": f"Destination location '{destination_location_query}' not found."}
    if src_loc.id == dest_loc.id: return {"error": "Source and destination locations must differ."}
    
    payload = {"product_id": str(product.id), "location_id": str(src_loc.id), "destination_location_id": str(dest_loc.id), "quantity": quantity, "notes": "Prepared by Copilot"}
    
    return _create_proposal(db, principal, "transfer", payload, 
                            display_title=f"Stock Transfer: {product.name}",
                            display_subtitle=f"From {src_loc.name} to {dest_loc.name}",
                            display_quantity=f"{quantity} {product.unit.value}")
