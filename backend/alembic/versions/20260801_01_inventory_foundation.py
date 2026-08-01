"""Create catalogue and inventory ledger tables.

Revision ID: 20260801_01
Revises:
Create Date: 2026-08-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260801_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # These are database-level PostgreSQL enum types.  We explicitly create
    # each type once, then disable implicit creation when the type is attached
    # to its table column.  Otherwise ``create_table`` emits CREATE TYPE again.
    unit = postgresql.ENUM("piece", "packet", "box", "kg", "gram", "litre", "ml", name="unit", create_type=False)
    location_type = postgresql.ENUM("store", "warehouse", "godown", "shelf", "other", name="location_type", create_type=False)
    movement_type = postgresql.ENUM("opening_stock", "receipt", "sale", "return", "adjustment", "transfer_out", "transfer_in", name="movement_type", create_type=False)
    bind = op.get_bind()
    unit.create(bind, checkfirst=True)
    location_type.create(bind, checkfirst=True)
    movement_type.create(bind, checkfirst=True)
    op.create_table("product_categories", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", sa.String(128), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("organization_id", "name", name="uq_category_org_name"))
    op.create_table("products", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", sa.String(128), nullable=False), sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("sku", sa.String(64), nullable=False), sa.Column("unit", unit, nullable=False), sa.Column("hsn_sac", sa.String(8)), sa.Column("cost_price", sa.Numeric(12,2), nullable=False), sa.Column("selling_price", sa.Numeric(12,2), nullable=False), sa.Column("gst_rate", sa.Numeric(5,2), nullable=False), sa.Column("reorder_level", sa.Numeric(14,3), nullable=False, server_default="0"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.ForeignKeyConstraint(["category_id"],["product_categories.id"]), sa.UniqueConstraint("organization_id","sku",name="uq_product_org_sku"))
    op.create_table("inventory_locations", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", sa.String(128), nullable=False), sa.Column("name", sa.String(100), nullable=False), sa.Column("location_type", location_type, nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("organization_id","name",name="uq_location_org_name"))
    op.create_table("suppliers", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", sa.String(128), nullable=False), sa.Column("name",sa.String(160),nullable=False),sa.Column("contact_person",sa.String(120),nullable=False),sa.Column("phone",sa.String(20),nullable=False),sa.Column("email",sa.String(254)),sa.Column("address",sa.Text()),sa.Column("is_active",sa.Boolean(),nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("inventory_balances", sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True), sa.Column("organization_id", sa.String(128), nullable=False), sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("available_quantity", sa.Numeric(14,3), nullable=False, server_default="0"), sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False), sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False), sa.ForeignKeyConstraint(["product_id"],["products.id"]),sa.ForeignKeyConstraint(["location_id"],["inventory_locations.id"]),sa.UniqueConstraint("organization_id","product_id","location_id",name="uq_balance_org_product_location"))
    op.create_table("stock_movements",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("organization_id",sa.String(128),nullable=False),sa.Column("product_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("location_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("movement_type",movement_type,nullable=False),sa.Column("quantity_delta",sa.Numeric(14,3),nullable=False),sa.Column("reference_id",postgresql.UUID(as_uuid=True)),sa.Column("notes",sa.Text()),sa.Column("occurred_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("created_by",sa.String(128),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.ForeignKeyConstraint(["product_id"],["products.id"]),sa.ForeignKeyConstraint(["location_id"],["inventory_locations.id"]))
def downgrade() -> None:
    op.drop_table("stock_movements"); op.drop_table("inventory_balances"); op.drop_table("suppliers"); op.drop_table("inventory_locations"); op.drop_table("products"); op.drop_table("product_categories")
    bind = op.get_bind()
    postgresql.ENUM(name="movement_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="location_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="unit").drop(bind, checkfirst=True)
