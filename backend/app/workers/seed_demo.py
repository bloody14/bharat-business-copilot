"""Development-only kirana demonstration seed. Run: python -m app.workers.seed_demo."""
from decimal import Decimal
from app.core.database import Base, SessionLocal, engine
from app.domain.inventory.models import InventoryLocation, LocationType, Product, Unit

ORG="org_kirana_demo"
def main() -> None:
    Base.metadata.create_all(engine)
    db=SessionLocal()
    try:
        store=InventoryLocation(organization_id=ORG,name="Main Kirana Store",location_type=LocationType.store)
        godown=InventoryLocation(organization_id=ORG,name="Back Godown",location_type=LocationType.godown)
        db.add_all([store,godown])
        for name,sku,unit,cost,sell,reorder in [("Fortune Sunflower Oil 1 L","FORTUNE-SUN-1L",Unit.piece,112,135,10),("Aashirvaad Atta 5 kg","AASH-ATTA-5KG",Unit.packet,245,285,8),("Tata Salt 1 kg","TATA-SALT-1KG",Unit.packet,20,25,12),("Maggi 2-Minute Noodles","MAGGI-70G",Unit.packet,11,14,15),("Parle-G Gold","PARLE-G-100G",Unit.packet,8,10,20),("Surf Excel Easy Wash 1kg","SURF-EXCEL-1KG",Unit.packet,105,130,6)]: db.add(Product(organization_id=ORG,name=name,sku=sku,unit=unit,cost_price=cost,selling_price=sell,gst_rate=Decimal("5"),reorder_level=reorder))
        db.commit()
    finally: db.close()
if __name__ == "__main__": main()
