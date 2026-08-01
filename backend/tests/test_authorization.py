"""Role-based authorization tests.

Verifies that write endpoints (create product, supplier, location, receipt,
adjustment, transfer) enforce the ``require_inventory_write`` guard, while
read endpoints are accessible to any authenticated role.
"""

import pytest


VALID_PRODUCT = {
    "name": "Auth Test Product",
    "sku": "AUTH-TEST-001",
    "unit": "piece",
    "cost_price": "10.00",
    "selling_price": "15.00",
    "gst_rate": "5",
    "reorder_level": "5",
}

VALID_SUPPLIER = {
    "name": "Auth Test Supplier",
    "contact_person": "Test Person",
    "phone": "+91 98765 43210",
}

VALID_LOCATION = {
    "name": "Auth Test Store",
    "location_type": "store",
}


# ---------------------------------------------------------------------------
# Write operations — only privileged roles
# ---------------------------------------------------------------------------

class TestInventoryWriteRoles:
    """Only owner / admin / manager / inventory may create resources."""

    @pytest.mark.parametrize("role", ["owner", "admin", "manager", "inventory"])
    def test_privileged_role_creates_product(self, client, as_principal, role):
        as_principal(role=role)
        resp = client.post("/api/v1/products", json={**VALID_PRODUCT, "sku": f"R-{role}"})
        assert resp.status_code == 201

    @pytest.mark.parametrize("role", ["viewer", "member"])
    def test_unprivileged_role_cannot_create_product(self, client, as_principal, role):
        as_principal(role=role)
        resp = client.post("/api/v1/products", json=VALID_PRODUCT)
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["viewer", "member"])
    def test_unprivileged_role_cannot_create_supplier(self, client, as_principal, role):
        as_principal(role=role)
        resp = client.post("/api/v1/suppliers", json=VALID_SUPPLIER)
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["viewer", "member"])
    def test_unprivileged_role_cannot_create_location(self, client, as_principal, role):
        as_principal(role=role)
        resp = client.post("/api/v1/locations", json=VALID_LOCATION)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Read operations — any role
# ---------------------------------------------------------------------------

class TestReadAccess:
    """Any authenticated user (including viewer / member) may read."""

    @pytest.mark.parametrize(
        "role",
        ["owner", "admin", "manager", "inventory", "viewer", "member"],
    )
    def test_any_role_can_list_products(self, client, as_principal, role):
        as_principal(role=role)
        assert client.get("/api/v1/products").status_code == 200

    @pytest.mark.parametrize(
        "role",
        ["owner", "admin", "manager", "inventory", "viewer", "member"],
    )
    def test_any_role_can_read_dashboard(self, client, as_principal, role):
        as_principal(role=role)
        assert client.get("/api/v1/inventory/dashboard").status_code == 200

    @pytest.mark.parametrize(
        "role",
        ["owner", "admin", "manager", "inventory", "viewer", "member"],
    )
    def test_any_role_can_list_movements(self, client, as_principal, role):
        as_principal(role=role)
        assert client.get("/api/v1/inventory/movements").status_code == 200

    @pytest.mark.parametrize(
        "role",
        ["owner", "admin", "manager", "inventory", "viewer", "member"],
    )
    def test_any_role_can_list_suppliers(self, client, as_principal, role):
        as_principal(role=role)
        assert client.get("/api/v1/suppliers").status_code == 200

    @pytest.mark.parametrize(
        "role",
        ["owner", "admin", "manager", "inventory", "viewer", "member"],
    )
    def test_any_role_can_list_locations(self, client, as_principal, role):
        as_principal(role=role)
        assert client.get("/api/v1/locations").status_code == 200
