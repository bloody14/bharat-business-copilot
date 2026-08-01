"""Development-only kirana demonstration seed. Run: python -m app.workers.seed_demo."""
import os
from decimal import Decimal
from sqlalchemy import select
from app.core.database import Base, SessionLocal, engine
from app.domain.inventory.models import InventoryLocation, LocationType, Product, Unit

ORG = os.getenv("DEMO_ORGANIZATION_ID", "org_kirana_demo")

def main() -> None:
    if ORG == "org_kirana_demo":
        print("WARNING: Using legacy org_kirana_demo fallback. For live demo, set DEMO_ORGANIZATION_ID.")
    else:
        print(f"Seeding demo data for organization: {ORG}")

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # Idempotent locations
        store = db.scalar(select(InventoryLocation).where(InventoryLocation.organization_id == ORG, InventoryLocation.name == "Main Kirana Store"))
        if not store:
            store = InventoryLocation(organization_id=ORG, name="Main Kirana Store", location_type=LocationType.store)
            db.add(store)

        godown = db.scalar(select(InventoryLocation).where(InventoryLocation.organization_id == ORG, InventoryLocation.name == "Back Godown"))
        if not godown:
            godown = InventoryLocation(organization_id=ORG, name="Back Godown", location_type=LocationType.godown)
            db.add(godown)

        # Idempotent products
        products_data = [
            ("Fortune Sunflower Oil 1 L", "FORTUNE-SUN-1L", Unit.piece, 112, 135, 10),
            ("Aashirvaad Atta 5 kg", "AASH-ATTA-5KG", Unit.packet, 245, 285, 8),
            ("Tata Salt 1 kg", "TATA-SALT-1KG", Unit.packet, 20, 25, 12),
            ("Maggi 2-Minute Noodles", "MAGGI-70G", Unit.packet, 11, 14, 15),
            ("Parle-G Gold", "PARLE-G-100G", Unit.packet, 8, 10, 20),
            ("Surf Excel Easy Wash 1kg", "SURF-EXCEL-1KG", Unit.packet, 105, 130, 6)
        ]

        for name, sku, unit, cost, sell, reorder in products_data:
            existing = db.scalar(select(Product).where(Product.organization_id == ORG, Product.sku == sku))
            if not existing:
                db.add(Product(
                    organization_id=ORG, name=name, sku=sku, unit=unit,
                    cost_price=cost, selling_price=sell, gst_rate=Decimal("5"), reorder_level=reorder
                ))

        db.commit()
        print("Seeding complete.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
