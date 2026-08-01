"""Tests for the existing inventory CRUD and append-only ledger endpoints.

Covers: products, suppliers, locations, receipts, adjustments, transfers,
stock movements, dashboard summary, and negative-stock protection.

All tests use the transactional ``client`` fixture (org_test_a / owner).
"""

from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

PRODUCT = {
    "name": "Test Atta 5kg",
    "sku": "TEST-ATTA-5KG",
    "unit": "packet",
    "cost_price": "245.00",
    "selling_price": "285.00",
    "gst_rate": "5",
    "reorder_level": "8",
}

SUPPLIER = {
    "name": "Test Supplier",
    "contact_person": "Ravi Kumar",
    "phone": "+91 98765 43210",
}

LOCATION_STORE = {"name": "Test Store", "location_type": "store"}
LOCATION_GODOWN = {"name": "Test Godown", "location_type": "godown"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_product(client, sku="TEST-001", **overrides):
    data = {**PRODUCT, "sku": sku, **overrides}
    resp = client.post("/api/v1/products", json=data)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_location(client, name="Test Store", loc_type="store"):
    resp = client.post(
        "/api/v1/locations",
        json={"name": name, "location_type": loc_type},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _receipt(client, product_id, location_id, quantity):
    resp = client.post(
        "/api/v1/inventory/receipts",
        json={
            "product_id": product_id,
            "location_id": location_id,
            "quantity": str(quantity),
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════
# Products
# ═══════════════════════════════════════════════════════════════════════


class TestProducts:
    def test_empty_list(self, client):
        assert client.get("/api/v1/products").json() == []

    def test_create_returns_correct_fields(self, client):
        resp = client.post("/api/v1/products", json=PRODUCT)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["name"] == "Test Atta 5kg"
        assert body["sku"] == "TEST-ATTA-5KG"
        assert body["unit"] == "packet"
        assert Decimal(body["available_quantity"]) == 0

    def test_create_and_list(self, client):
        client.post("/api/v1/products", json=PRODUCT)
        products = client.get("/api/v1/products").json()
        assert len(products) == 1
        assert products[0]["name"] == "Test Atta 5kg"

    def test_duplicate_sku_rejected(self, client):
        client.post("/api/v1/products", json=PRODUCT)
        resp = client.post("/api/v1/products", json=PRODUCT)
        assert resp.status_code == 409

    def test_sku_normalised_to_uppercase(self, client):
        resp = client.post(
            "/api/v1/products",
            json={**PRODUCT, "sku": "  lower-sku  "},
        )
        assert resp.json()["sku"] == "LOWER-SKU"

    def test_invalid_gst_rate_rejected(self, client):
        resp = client.post(
            "/api/v1/products",
            json={**PRODUCT, "sku": "GST-BAD", "gst_rate": "10"},
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("rate", ["0", "5", "12", "18", "28"])
    def test_valid_gst_rates_accepted(self, client, rate):
        resp = client.post(
            "/api/v1/products",
            json={**PRODUCT, "sku": f"GST-{rate}", "gst_rate": rate},
        )
        assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════
# Suppliers
# ═══════════════════════════════════════════════════════════════════════


class TestSuppliers:
    def test_empty_list(self, client):
        assert client.get("/api/v1/suppliers").json() == []

    def test_create_and_list(self, client):
        resp = client.post("/api/v1/suppliers", json=SUPPLIER)
        assert resp.status_code == 201
        suppliers = client.get("/api/v1/suppliers").json()
        assert len(suppliers) == 1
        assert suppliers[0]["name"] == "Test Supplier"
        assert suppliers[0]["phone"] == "+91 98765 43210"


# ═══════════════════════════════════════════════════════════════════════
# Locations
# ═══════════════════════════════════════════════════════════════════════


class TestLocations:
    def test_empty_list(self, client):
        assert client.get("/api/v1/locations").json() == []

    def test_create_and_list(self, client):
        resp = client.post("/api/v1/locations", json=LOCATION_STORE)
        assert resp.status_code == 201
        locations = client.get("/api/v1/locations").json()
        assert len(locations) == 1
        assert locations[0]["name"] == "Test Store"
        assert locations[0]["location_type"] == "store"

    def test_duplicate_location_rejected(self, client):
        client.post("/api/v1/locations", json=LOCATION_STORE)
        resp = client.post("/api/v1/locations", json=LOCATION_STORE)
        assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════════════════
# Receipts
# ═══════════════════════════════════════════════════════════════════════


class TestReceipts:
    def test_receipt_increases_balance(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 20)
        products = client.get("/api/v1/products").json()
        assert Decimal(products[0]["available_quantity"]) == 20

    def test_multiple_receipts_accumulate(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 10)
        _receipt(client, pid, lid, 5)
        products = client.get("/api/v1/products").json()
        assert Decimal(products[0]["available_quantity"]) == 15

    def test_receipt_creates_movement_record(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 7)
        movements = client.get("/api/v1/inventory/movements").json()
        assert len(movements) == 1
        assert movements[0]["type"] == "receipt"
        assert Decimal(movements[0]["quantity_delta"]) == 7

    def test_receipt_nonexistent_product_returns_404(self, client):
        lid = _create_location(client)
        resp = client.post(
            "/api/v1/inventory/receipts",
            json={
                "product_id": "00000000-0000-0000-0000-000000000001",
                "location_id": lid,
                "quantity": "10",
            },
        )
        assert resp.status_code == 404

    def test_receipt_nonexistent_location_returns_404(self, client):
        pid = _create_product(client)
        resp = client.post(
            "/api/v1/inventory/receipts",
            json={
                "product_id": pid,
                "location_id": "00000000-0000-0000-0000-000000000001",
                "quantity": "10",
            },
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# Adjustments
# ═══════════════════════════════════════════════════════════════════════


class TestAdjustments:
    def test_adjustment_adds_stock(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        resp = client.post(
            "/api/v1/inventory/adjustments",
            json={
                "product_id": pid,
                "location_id": lid,
                "quantity": "5",
                "notes": "Opening stock count",
            },
        )
        assert resp.status_code == 201
        products = client.get("/api/v1/products").json()
        assert Decimal(products[0]["available_quantity"]) == 5

    def test_adjustment_creates_movement_record(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        client.post(
            "/api/v1/inventory/adjustments",
            json={"product_id": pid, "location_id": lid, "quantity": "3"},
        )
        movements = client.get("/api/v1/inventory/movements").json()
        assert len(movements) == 1
        assert movements[0]["type"] == "adjustment"
        assert Decimal(movements[0]["quantity_delta"]) == 3

    def test_adjustment_can_decrease_stock(self, client):
        """Phase 2 fix: Adjustments can now be negative to decrease stock."""
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 10)

        # quantity=0 is still rejected by the schema
        resp = client.post(
            "/api/v1/inventory/adjustments",
            json={"product_id": pid, "location_id": lid, "quantity": "0"},
        )
        assert resp.status_code == 422

        # Negative quantity is accepted and reduces stock
        resp = client.post(
            "/api/v1/inventory/adjustments",
            json={"product_id": pid, "location_id": lid, "quantity": "-3"},
        )
        assert resp.status_code == 201

        products = client.get("/api/v1/products").json()
        assert Decimal(products[0]["available_quantity"]) == 7

        movements = client.get("/api/v1/inventory/movements").json()
        deltas = sorted(Decimal(m["quantity_delta"]) for m in movements)
        assert deltas == [-3, 10]


# ═══════════════════════════════════════════════════════════════════════
# Transfers
# ═══════════════════════════════════════════════════════════════════════


class TestTransfers:
    def test_transfer_preserves_total_quantity(self, client):
        pid = _create_product(client)
        lid_src = _create_location(client, "Source Store")
        lid_dst = _create_location(client, "Dest Godown", "godown")
        _receipt(client, pid, lid_src, 50)

        resp = client.post(
            "/api/v1/inventory/transfers",
            json={
                "product_id": pid,
                "location_id": lid_src,
                "destination_location_id": lid_dst,
                "quantity": "20",
            },
        )
        assert resp.status_code == 201
        assert "transfer_id" in resp.json()

        # Total quantity across all locations should remain 50.
        products = client.get("/api/v1/products").json()
        assert Decimal(products[0]["available_quantity"]) == 50

    def test_transfer_creates_paired_movements(self, client):
        pid = _create_product(client)
        lid_src = _create_location(client, "Source")
        lid_dst = _create_location(client, "Dest", "godown")
        _receipt(client, pid, lid_src, 30)

        resp = client.post(
            "/api/v1/inventory/transfers",
            json={
                "product_id": pid,
                "location_id": lid_src,
                "destination_location_id": lid_dst,
                "quantity": "10",
            },
        )
        assert resp.status_code == 201

        movements = client.get("/api/v1/inventory/movements").json()
        # 1 receipt + 2 transfer movements = 3
        assert len(movements) == 3
        transfer_types = {m["type"] for m in movements if "transfer" in m["type"]}
        assert transfer_types == {"transfer_out", "transfer_in"}

        # The paired movements share a reference_id.
        transfer_refs = {
            m["reference_id"]
            for m in movements
            if "transfer" in m["type"]
        }
        assert len(transfer_refs) == 1  # same reference_id

    def test_transfer_same_location_rejected(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 10)

        resp = client.post(
            "/api/v1/inventory/transfers",
            json={
                "product_id": pid,
                "location_id": lid,
                "destination_location_id": lid,
                "quantity": "5",
            },
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# Negative stock protection
# ═══════════════════════════════════════════════════════════════════════


class TestNegativeStockProtection:
    def test_transfer_more_than_available_rejected(self, client):
        pid = _create_product(client)
        lid_src = _create_location(client, "Source")
        lid_dst = _create_location(client, "Dest", "godown")
        _receipt(client, pid, lid_src, 10)

        resp = client.post(
            "/api/v1/inventory/transfers",
            json={
                "product_id": pid,
                "location_id": lid_src,
                "destination_location_id": lid_dst,
                "quantity": "20",
            },
        )
        assert resp.status_code == 422

    def test_transfer_exact_amount_succeeds(self, client):
        pid = _create_product(client)
        lid_src = _create_location(client, "Source")
        lid_dst = _create_location(client, "Dest", "godown")
        _receipt(client, pid, lid_src, 10)

        resp = client.post(
            "/api/v1/inventory/transfers",
            json={
                "product_id": pid,
                "location_id": lid_src,
                "destination_location_id": lid_dst,
                "quantity": "10",
            },
        )
        assert resp.status_code == 201


# ═══════════════════════════════════════════════════════════════════════
# Movements
# ═══════════════════════════════════════════════════════════════════════


class TestMovements:
    def test_movements_listed_with_correct_data(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 1)
        _receipt(client, pid, lid, 2)

        movements = client.get("/api/v1/inventory/movements").json()
        assert len(movements) == 2
        deltas = sorted(Decimal(m["quantity_delta"]) for m in movements)
        assert deltas == [1, 2]
        # Both should be receipt type.
        assert all(m["type"] == "receipt" for m in movements)

    def test_movements_include_product_and_location(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 5)

        movements = client.get("/api/v1/inventory/movements").json()
        assert len(movements) == 1
        assert movements[0]["product_id"] == pid
        assert movements[0]["location_id"] == lid
        assert "occurred_at" in movements[0]


# ═══════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════


class TestDashboard:
    def test_empty_dashboard(self, client):
        data = client.get("/api/v1/inventory/dashboard").json()
        assert data["total_products"] == 0
        assert Decimal(data["total_stock_quantity"]) == 0
        assert data["low_stock_products"] == 0
        assert data["out_of_stock_products"] == 0
        assert data["recent_movements"] == []

    def test_dashboard_with_stock(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 100)

        data = client.get("/api/v1/inventory/dashboard").json()
        assert data["total_products"] == 1
        assert Decimal(data["total_stock_quantity"]) == 100
        assert data["low_stock_products"] == 0
        assert data["out_of_stock_products"] == 0

    def test_dashboard_low_stock_detection(self, client):
        """Product with quantity below reorder_level is flagged low-stock."""
        pid = _create_product(client, reorder_level="8")
        lid = _create_location(client)
        _receipt(client, pid, lid, 5)  # 5 <= 8 → low stock

        data = client.get("/api/v1/inventory/dashboard").json()
        assert data["low_stock_products"] == 1

    def test_dashboard_out_of_stock_detection(self, client):
        """Product with zero stock is flagged out-of-stock."""
        _create_product(client)  # no receipt → qty = 0
        data = client.get("/api/v1/inventory/dashboard").json()
        assert data["out_of_stock_products"] == 1

    def test_dashboard_includes_recent_movements(self, client):
        pid = _create_product(client)
        lid = _create_location(client)
        _receipt(client, pid, lid, 10)

        data = client.get("/api/v1/inventory/dashboard").json()
        assert len(data["recent_movements"]) == 1
        assert data["recent_movements"][0]["type"] == "receipt"
