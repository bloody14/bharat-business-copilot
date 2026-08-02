import argparse
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.domain.inventory.models import Product, InventoryLocation, Unit, LocationType, InventoryMovement, MovementType, InventoryBalance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_tenant(org_id: str):
    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        # Delete existing tenant data carefully in the correct order
        logger.info(f"Clearing existing data for organization: {org_id}")
        db.query(InventoryMovement).filter_by(organization_id=org_id).delete()
        db.query(InventoryBalance).filter_by(organization_id=org_id).delete()
        db.query(Product).filter_by(organization_id=org_id).delete()
        db.query(InventoryLocation).filter_by(organization_id=org_id).delete()
        
        # Insert locations
        logger.info("Inserting demo locations...")
        main_shop = InventoryLocation(organization_id=org_id, name="Main Shop", location_type=LocationType.store)
        back_godown = InventoryLocation(organization_id=org_id, name="Back Godown", location_type=LocationType.warehouse)
        db.add_all([main_shop, back_godown])
        db.flush()
        
        # Insert products
        logger.info("Inserting demo products...")
        tata_salt = Product(organization_id=org_id, name="Tata Salt 1kg", sku="TATA_SALT", unit=Unit.packet, cost_price=20, selling_price=25, gst_rate=5)
        parle_g = Product(organization_id=org_id, name="Parle-G Gold", sku="PARLE_G", unit=Unit.packet, cost_price=10, selling_price=15, gst_rate=12)
        tata_tea = Product(organization_id=org_id, name="Tata Tea Gold", sku="TATA_TEA", unit=Unit.packet, cost_price=100, selling_price=120, gst_rate=5)
        
        db.add_all([tata_salt, parle_g, tata_tea])
        db.flush()
        
        # Insert initial balances and movements
        logger.info("Inserting demo stock balances...")
        
        # Main shop receives 50 packets of Tata Salt
        mov1 = InventoryMovement(
            organization_id=org_id,
            product_id=tata_salt.id,
            movement_type=MovementType.receipt,
            quantity=50,
            destination_location_id=main_shop.id,
            reference_number="DEMO-IN-001"
        )
        bal1 = InventoryBalance(organization_id=org_id, product_id=tata_salt.id, location_id=main_shop.id, available_quantity=50)
        
        # Back Godown receives 100 packets of Parle G
        mov2 = InventoryMovement(
            organization_id=org_id,
            product_id=parle_g.id,
            movement_type=MovementType.receipt,
            quantity=100,
            destination_location_id=back_godown.id,
            reference_number="DEMO-IN-002"
        )
        bal2 = InventoryBalance(organization_id=org_id, product_id=parle_g.id, location_id=back_godown.id, available_quantity=100)
        
        db.add_all([mov1, bal1, mov2, bal2])
        
        db.commit()
        logger.info(f"Demo seed complete for organization: {org_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed database for a specific tenant")
    parser.add_argument("org_id", type=str, help="The organization_id (e.g. from Clerk) to reset and seed")
    args = parser.parse_args()
    seed_tenant(args.org_id)
