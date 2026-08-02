"""Tenant-isolated catalogue and append-only inventory ledger routes."""
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import Principal, get_principal
from app.domain.inventory.models import InventoryBalance, InventoryLocation, LocationType, MovementType, Product, StockMovement, Supplier, Unit

router = APIRouter()

def require_inventory_write(principal: Principal = Depends(get_principal)) -> Principal:
    if principal.role not in {"owner", "admin", "manager", "inventory"}: raise HTTPException(403, "Inventory write permission required")
    return principal
class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=160); sku: str = Field(min_length=2,max_length=64); unit: Unit; hsn_sac: str|None = Field(default=None,pattern=r"^\d{4,8}$"); cost_price: Decimal = Field(ge=0); selling_price: Decimal = Field(ge=0); gst_rate: Decimal; reorder_level: Decimal = Field(default=0,ge=0); is_active: bool = True
    @field_validator("sku")
    @classmethod
    def sku_normalized(cls, value: str) -> str: return value.strip().upper()
    @field_validator("gst_rate")
    @classmethod
    def valid_gst(cls, value: Decimal) -> Decimal:
        if value not in {Decimal("0"),Decimal("5"),Decimal("12"),Decimal("18"),Decimal("28")}: raise ValueError("GST rate must be 0, 5, 12, 18 or 28")
        return value
class SupplierInput(BaseModel): name:str=Field(min_length=2,max_length=160); contact_person:str=Field(min_length=2,max_length=120); phone:str=Field(pattern=r"^[+0-9 ()-]{8,20}$"); email:str|None=None; address:str|None=Field(default=None,max_length=1000)
class LocationInput(BaseModel): name:str=Field(min_length=2,max_length=100); location_type:LocationType; is_active:bool=True
class BaseMovementInput(BaseModel): product_id:uuid.UUID; location_id:uuid.UUID; notes:str|None=Field(default=None,max_length=500)
class MovementInput(BaseMovementInput): quantity:Decimal=Field(gt=0)
class AdjustmentInput(BaseMovementInput):
    quantity:Decimal
    @field_validator("quantity")
    @classmethod
    def non_zero(cls, value: Decimal) -> Decimal:
        if value == Decimal("0"): raise ValueError("Quantity must not be zero")
        return value
class TransferInput(MovementInput): destination_location_id:uuid.UUID
def product_json(p:Product, quantity:Decimal=Decimal("0")) -> dict:
    return {"id":str(p.id),"name":p.name,"sku":p.sku,"unit":p.unit.value,"hsn_sac":p.hsn_sac,"cost_price":str(p.cost_price),"selling_price":str(p.selling_price),"gst_rate":str(p.gst_rate),"reorder_level":str(p.reorder_level),"available_quantity":str(quantity),"is_active":p.is_active}
def quantity_map(db:Session, org:str) -> dict:
    return dict(db.execute(select(InventoryBalance.product_id,func.coalesce(func.sum(InventoryBalance.available_quantity),0)).where(InventoryBalance.organization_id==org).group_by(InventoryBalance.product_id)).all())
@router.get("/products")
def products(principal:Principal=Depends(get_principal), db:Session=Depends(get_db)):
    q=quantity_map(db,principal.organization_id); return [product_json(p,Decimal(str(q.get(p.id,0)))) for p in db.scalars(select(Product).where(Product.organization_id==principal.organization_id).order_by(Product.name))]
@router.post("/products",status_code=201)
def create_product(data:ProductInput, principal:Principal=Depends(require_inventory_write), db:Session=Depends(get_db)):
    product=Product(organization_id=principal.organization_id,**data.model_dump()); db.add(product)
    try: db.commit()
    except IntegrityError as error: db.rollback(); raise HTTPException(409,"SKU already exists") from error
    db.refresh(product); return product_json(product)
@router.get("/suppliers")
def suppliers(principal:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    return [{"id":str(s.id),"name":s.name,"contact_person":s.contact_person,"phone":s.phone,"email":s.email,"address":s.address,"is_active":s.is_active} for s in db.scalars(select(Supplier).where(Supplier.organization_id==principal.organization_id))]
@router.post("/suppliers",status_code=201)
def create_supplier(data:SupplierInput,principal:Principal=Depends(require_inventory_write),db:Session=Depends(get_db)):
    supplier=Supplier(organization_id=principal.organization_id,**data.model_dump()); db.add(supplier); db.commit(); db.refresh(supplier); return {"id":str(supplier.id),"name":supplier.name}
@router.get("/locations")
def locations(principal:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    return [{"id":str(x.id),"name":x.name,"location_type":x.location_type.value,"is_active":x.is_active} for x in db.scalars(select(InventoryLocation).where(InventoryLocation.organization_id==principal.organization_id))]
@router.post("/locations",status_code=201)
def create_location(data:LocationInput,principal:Principal=Depends(require_inventory_write),db:Session=Depends(get_db)):
    item=InventoryLocation(organization_id=principal.organization_id,**data.model_dump()); db.add(item)
    try: db.commit()
    except IntegrityError as error: db.rollback(); raise HTTPException(409,"Location already exists") from error
    db.refresh(item); return {"id":str(item.id),"name":item.name}
from app.domain.inventory.service import post_movement

@router.post("/inventory/receipts",status_code=201)
def receipt(data:MovementInput,principal:Principal=Depends(require_inventory_write),db:Session=Depends(get_db)):
    item=post_movement(data.product_id, data.location_id, data.quantity, data.notes, MovementType.receipt, principal, db)
    db.commit()
    return {"id":str(item.id),"quantity_delta":str(item.quantity_delta)}

@router.post("/inventory/adjustments",status_code=201)
def adjustment(data:AdjustmentInput,principal:Principal=Depends(require_inventory_write),db:Session=Depends(get_db)):
    item=post_movement(data.product_id, data.location_id, data.quantity, data.notes, MovementType.adjustment, principal, db)
    db.commit()
    return {"id":str(item.id)}

@router.post("/inventory/transfers",status_code=201)
def transfer(data:TransferInput,principal:Principal=Depends(require_inventory_write),db:Session=Depends(get_db)):
    if data.location_id==data.destination_location_id: raise HTTPException(422,"Transfer locations must differ")
    ref=uuid.uuid4()
    post_movement(data.product_id, data.location_id, data.quantity, data.notes, MovementType.transfer_out, principal, db, -1, ref)
    post_movement(data.product_id, data.destination_location_id, data.quantity, data.notes, MovementType.transfer_in, principal, db, 1, ref)
    db.commit()
    return {"transfer_id":str(ref)}
@router.get("/inventory/movements")
def movements(principal:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    rows=db.scalars(select(StockMovement).where(StockMovement.organization_id==principal.organization_id).order_by(StockMovement.occurred_at.desc())).all(); return [{"id":str(m.id),"product_id":str(m.product_id),"location_id":str(m.location_id),"type":m.movement_type.value,"quantity_delta":str(m.quantity_delta),"reference_id":str(m.reference_id) if m.reference_id else None,"occurred_at":m.occurred_at} for m in rows]
@router.get("/inventory/dashboard")
def dashboard(principal:Principal=Depends(get_principal),db:Session=Depends(get_db)):
    items=db.scalars(select(Product).where(Product.organization_id==principal.organization_id)).all(); quantities=quantity_map(db,principal.organization_id); amounts=[Decimal(str(quantities.get(x.id,0))) for x in items]; return {"total_products":len(items),"total_stock_quantity":str(sum(amounts)) ,"low_stock_products":sum(q<=Decimal(str(x.reorder_level)) for x,q in zip(items,amounts)),"out_of_stock_products":sum(q<=0 for q in amounts),"recent_movements":movements(principal,db)[:10]}
