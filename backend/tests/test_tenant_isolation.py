"""Multi-tenancy / tenant isolation tests.

Verifies that data created by organisation A is invisible to organisation B,
and that cross-tenant operations (e.g. receipting Org A's product from Org B)
are correctly rejected.
"""

from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Shared test data (per-org products use different SKUs to avoid collisions)
# ---------------------------------------------------------------------------

PRODUCT_A = {
    "name": "Org A Product",
    "sku": "ORG-A-001",
    "unit": "piece",
    "cost_price": "10.00",
    "selling_price": "15.00",
    "gst_rate": "5",
}

PRODUCT_B = {
    "name": "Org B Product",
    "sku": "ORG-B-001",
    "unit": "packet",
    "cost_price": "20.00",
    "selling_price": "30.00",
    "gst_rate": "12",
}

LOCATION = {"name": "Test Store", "location_type": "store"}
SUPPLIER = {
    "name": "Isolation Supplier",
    "contact_person": "Contact",
    "phone": "+91 1234567890",
}


# ═══════════════════════════════════════════════════════════════════════
# Product isolation
# ═══════════════════════════════════════════════════════════════════════


class TestProductIsolation:
    def test_org_b_cannot_see_org_a_products(self, client, as_principal):
        # Org A creates a product.
        client.post("/api/v1/products", json=PRODUCT_A)
        assert len(client.get("/api/v1/products").json()) == 1

        # Switch to Org B — should see nothing.
        as_principal(org_id="org_test_b")
        assert client.get("/api/v1/products").json() == []

    def test_each_org_sees_only_own_products(self, client, as_principal):
        # Org A creates a product.
        client.post("/api/v1/products", json=PRODUCT_A)

        # Org B creates its own product.
        as_principal(org_id="org_test_b")
        client.post("/api/v1/products", json=PRODUCT_B)

        # Org B sees only its product.
        products_b = client.get("/api/v1/products").json()
        assert len(products_b) == 1
        assert products_b[0]["name"] == "Org B Product"

        # Switch back — Org A sees only its product.
        as_principal(org_id="org_test_a")
        products_a = client.get("/api/v1/products").json()
        assert len(products_a) == 1
        assert products_a[0]["name"] == "Org A Product"


# ═══════════════════════════════════════════════════════════════════════
# Supplier isolation
# ═══════════════════════════════════════════════════════════════════════


class TestSupplierIsolation:
    def test_org_b_cannot_see_org_a_suppliers(self, client, as_principal):
        client.post("/api/v1/suppliers", json=SUPPLIER)
        assert len(client.get("/api/v1/suppliers").json()) == 1

        as_principal(org_id="org_test_b")
        assert client.get("/api/v1/suppliers").json() == []


# ═══════════════════════════════════════════════════════════════════════
# Location isolation
# ═══════════════════════════════════════════════════════════════════════


class TestLocationIsolation:
    def test_org_b_cannot_see_org_a_locations(self, client, as_principal):
        client.post("/api/v1/locations", json=LOCATION)
        assert len(client.get("/api/v1/locations").json()) == 1

        as_principal(org_id="org_test_b")
        assert client.get("/api/v1/locations").json() == []


# ═══════════════════════════════════════════════════════════════════════
# Movement isolation
# ═══════════════════════════════════════════════════════════════════════


class TestMovementIsolation:
    def test_org_b_cannot_see_org_a_movements(self, client, as_principal):
        # Org A creates stock.
        resp_p = client.post("/api/v1/products", json=PRODUCT_A)
        pid = resp_p.json()["id"]
        resp_l = client.post("/api/v1/locations", json=LOCATION)
        lid = resp_l.json()["id"]
        client.post(
            "/api/v1/inventory/receipts",
            json={"product_id": pid, "location_id": lid, "quantity": "10"},
        )
        assert len(client.get("/api/v1/inventory/movements").json()) == 1

        # Org B sees no movements.
        as_principal(org_id="org_test_b")
        assert client.get("/api/v1/inventory/movements").json() == []

    def test_org_b_cannot_receipt_org_a_product(self, client, as_principal):
        """Cross-tenant receipt must be rejected — product not found for Org B."""
        # Org A creates a product.
        resp_p = client.post("/api/v1/products", json=PRODUCT_A)
        pid_a = resp_p.json()["id"]

        # Org B creates its own location.
        as_principal(org_id="org_test_b")
        resp_l = client.post("/api/v1/locations", json=LOCATION)
        lid_b = resp_l.json()["id"]

        # Org B tries to receipt Org A's product into its own location.
        resp = client.post(
            "/api/v1/inventory/receipts",
            json={"product_id": pid_a, "location_id": lid_b, "quantity": "10"},
        )
        assert resp.status_code == 404

    def test_org_b_cannot_receipt_into_org_a_location(self, client, as_principal):
        """Cross-tenant receipt must be rejected — location not found for Org B."""
        # Org A creates a location.
        resp_l = client.post("/api/v1/locations", json=LOCATION)
        lid_a = resp_l.json()["id"]

        # Org B creates its own product.
        as_principal(org_id="org_test_b")
        resp_p = client.post("/api/v1/products", json=PRODUCT_B)
        pid_b = resp_p.json()["id"]

        # Org B tries to receipt its product into Org A's location.
        resp = client.post(
            "/api/v1/inventory/receipts",
            json={"product_id": pid_b, "location_id": lid_a, "quantity": "10"},
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# Dashboard isolation
# ═══════════════════════════════════════════════════════════════════════


class TestDashboardIsolation:
    def test_dashboard_shows_only_own_data(self, client, as_principal):
        # Org A has a product with stock.
        resp_p = client.post("/api/v1/products", json=PRODUCT_A)
        pid = resp_p.json()["id"]
        resp_l = client.post("/api/v1/locations", json=LOCATION)
        lid = resp_l.json()["id"]
        client.post(
            "/api/v1/inventory/receipts",
            json={"product_id": pid, "location_id": lid, "quantity": "100"},
        )

        # Org B's dashboard should be completely empty.
        as_principal(org_id="org_test_b")
        data = client.get("/api/v1/inventory/dashboard").json()
        assert data["total_products"] == 0
        assert Decimal(data["total_stock_quantity"]) == 0
        assert data["recent_movements"] == []
