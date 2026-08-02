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
