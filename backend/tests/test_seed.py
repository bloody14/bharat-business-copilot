import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.domain.inventory.models import Product, InventoryLocation, InventoryMovement, InventoryBalance, LocationType, Unit
from app.scripts.seed_demo import seed_tenant

def test_seed_tenant_isolation(db: Session):
    # Setup Tenant B with data
    org_b = "org_test_b"
    p_b = Product(organization_id=org_b, name="Org B Product", sku="B_PROD", unit=Unit.packet, cost_price=10, selling_price=15, gst_rate=5)
    loc_b = InventoryLocation(organization_id=org_b, name="Org B Location", location_type=LocationType.store)
    db.add_all([p_b, loc_b])
    db.commit()
    
    # Run seed script for Tenant A
    org_a = "org_test_a"
    seed_tenant(org_a)
    
    # Assert Tenant A has seed data
    a_products = db.scalars(select(Product).where(Product.organization_id == org_a)).all()
    assert len(a_products) == 3
    
    # Assert Tenant B data was NOT modified or deleted by the truncate
    b_products = db.scalars(select(Product).where(Product.organization_id == org_b)).all()
    assert len(b_products) == 1
    assert b_products[0].sku == "B_PROD"
    
    # Clean up (normally handled by fixture rollbacks but since seed_tenant commits, we should delete)
    # The fixture rollback in conftest handles it, but just in case:
    # Actually, seed_tenant commits, so the test's transaction boundary might be broken depending on conftest.
    # We can just verify the isolation works here.
