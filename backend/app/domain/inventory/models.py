import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Unit(str, enum.Enum): piece="piece"; packet="packet"; box="box"; kg="kg"; gram="gram"; litre="litre"; ml="ml"
class LocationType(str, enum.Enum): store="store"; warehouse="warehouse"; godown="godown"; shelf="shelf"; other="other"
class MovementType(str, enum.Enum): opening_stock="opening_stock"; receipt="receipt"; sale="sale"; return_="return"; adjustment="adjustment"; transfer_out="transfer_out"; transfer_in="transfer_in"
class TenantModel(Base):
    __abstract__=True
    id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    organization_id: Mapped[str]=mapped_column(String(128),nullable=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
class ProductCategory(TenantModel):
    __tablename__="product_categories"; name: Mapped[str]=mapped_column(String(100),nullable=False); is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
    __table_args__=(UniqueConstraint("organization_id","name",name="uq_category_org_name"),)
class Product(TenantModel):
    __tablename__="products"; category_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True),ForeignKey("product_categories.id")); name: Mapped[str]=mapped_column(String(160),nullable=False); sku: Mapped[str]=mapped_column(String(64),nullable=False); unit: Mapped[Unit]=mapped_column(Enum(Unit,name="unit"),nullable=False); hsn_sac: Mapped[str|None]=mapped_column(String(8)); cost_price: Mapped[float]=mapped_column(Numeric(12,2),nullable=False); selling_price: Mapped[float]=mapped_column(Numeric(12,2),nullable=False); gst_rate: Mapped[float]=mapped_column(Numeric(5,2),nullable=False); reorder_level: Mapped[float]=mapped_column(Numeric(14,3),default=0,nullable=False); is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
    __table_args__=(UniqueConstraint("organization_id","sku",name="uq_product_org_sku"),)
class Supplier(TenantModel):
    __tablename__="suppliers"; name: Mapped[str]=mapped_column(String(160),nullable=False); contact_person: Mapped[str]=mapped_column(String(120),nullable=False); phone: Mapped[str]=mapped_column(String(20),nullable=False); email: Mapped[str|None]=mapped_column(String(254)); address: Mapped[str|None]=mapped_column(Text); is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
class InventoryLocation(TenantModel):
    __tablename__="inventory_locations"; name: Mapped[str]=mapped_column(String(100),nullable=False); location_type: Mapped[LocationType]=mapped_column(Enum(LocationType,name="location_type"),nullable=False); is_active: Mapped[bool]=mapped_column(Boolean,default=True,nullable=False)
    __table_args__=(UniqueConstraint("organization_id","name",name="uq_location_org_name"),)
class InventoryBalance(TenantModel):
    __tablename__="inventory_balances"; product_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("products.id"),nullable=False); location_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("inventory_locations.id"),nullable=False); available_quantity: Mapped[float]=mapped_column(Numeric(14,3),default=0,nullable=False); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
    __table_args__=(UniqueConstraint("organization_id","product_id","location_id",name="uq_balance_org_product_location"),)
class StockMovement(TenantModel):
    __tablename__="stock_movements"; product_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("products.id"),nullable=False); location_id: Mapped[uuid.UUID]=mapped_column(UUID(as_uuid=True),ForeignKey("inventory_locations.id"),nullable=False); movement_type: Mapped[MovementType]=mapped_column(Enum(MovementType,name="movement_type"),nullable=False); quantity_delta: Mapped[float]=mapped_column(Numeric(14,3),nullable=False); reference_id: Mapped[uuid.UUID|None]=mapped_column(UUID(as_uuid=True)); notes: Mapped[str|None]=mapped_column(Text); occurred_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False); created_by: Mapped[str]=mapped_column(String(128),nullable=False)
    __table_args__=(Index("ix_movement_org_product_time","organization_id","product_id","occurred_at"),)
