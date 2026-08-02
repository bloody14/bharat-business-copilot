import uuid
import datetime
import pytest
import threading
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.inventory.models import Product, InventoryLocation, InventoryBalance, LocationType, Unit
from app.domain.copilot.models import CopilotActionProposal

@pytest.fixture
def seed_data(db: Session):
    org = "org_test_a"
    p = Product(organization_id=org, name="Test Product", sku="TEST01", unit=Unit.piece, cost_price=10, selling_price=15, gst_rate=5)
    loc1 = InventoryLocation(organization_id=org, name="Main Store", location_type=LocationType.store)
    loc2 = InventoryLocation(organization_id=org, name="Godown", location_type=LocationType.warehouse)
    
    db.add_all([p, loc1, loc2])
    db.commit()
    db.refresh(p)
    db.refresh(loc1)
    db.refresh(loc2)
    return {"product": p, "loc1": loc1, "loc2": loc2}

def _mock_copilot_call(client, query):
    # In order to force Gemini to generate an action without an API key, we might need 
    # to monkeypatch the provider for these tests if we don't have the API key.
    # Wait, the other test `test_tenant_isolation_product_lookup` monkeypatched `GoogleGenAIProvider`.
    pass

# We must mock the provider for these tests to avoid hitting the real Gemini API (and we don't have a key in test env).
from app.domain.copilot.provider import MockProvider, ProviderResponse, ToolCallRequest
from app.api.v1.routes import copilot
from app.core.config import get_settings

def _mock_config():
    from app.core.config import Settings
    return Settings(gemini_api_key="fake", gemini_model="fake-model")

@pytest.fixture
def mock_provider_env(monkeypatch):
    # Base monkeypatch for config
    from app.main import app
    app.dependency_overrides[get_settings] = _mock_config
    
    def set_mock_responses(responses):
        def _fake_provider(api_key, model):
            return MockProvider(responses)
        monkeypatch.setattr(copilot, "GoogleGenAIProvider", _fake_provider)

    yield set_mock_responses
    app.dependency_overrides.pop(get_settings, None)

def test_prepare_receipt(client: TestClient, db: Session, seed_data: dict, mock_provider_env):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": 10})]),
        ProviderResponse(text="Prepared")
    ])
    
    response = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Receive 10 packets of TEST01 to Main Store"}
    )
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["action_proposals"]) == 1
    proposal = data["action_proposals"][0]
    assert proposal["action_type"] == "receipt"
    assert proposal["status"] == "pending"
    assert proposal["payload"]["quantity"] == 10
    
    balance = db.scalar(select(InventoryBalance).where(InventoryBalance.product_id == seed_data["product"].id))
    assert not balance or balance.available_quantity == 0

def test_execute_receipt_success(client: TestClient, db: Session, seed_data: dict, mock_provider_env):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": 15})]),
        ProviderResponse(text="Prepared")
    ])

    resp1 = client.post(
        "/api/v1/copilot/chat",
        json={"message": "Receive 15 units"}
    )
    action_id = resp1.json()["action_proposals"][0]["action_id"]

    resp2 = client.post(f"/api/v1/copilot/actions/{action_id}/execute")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "success"

    balance = db.scalar(select(InventoryBalance).where(InventoryBalance.product_id == seed_data["product"].id))
    assert balance.available_quantity == 15

    proposal = db.scalar(select(CopilotActionProposal).where(CopilotActionProposal.id == uuid.UUID(action_id)))
    assert proposal.status == "executed"

def test_duplicate_execution_idempotency(client: TestClient, db: Session, seed_data: dict, mock_provider_env):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": 5})]),
        ProviderResponse(text="Prepared")
    ])
    
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Receive 5 units"})
    action_id = resp1.json()["action_proposals"][0]["action_id"]

    client.post(f"/api/v1/copilot/actions/{action_id}/execute")

    resp3 = client.post(f"/api/v1/copilot/actions/{action_id}/execute")
    assert resp3.status_code == 400

def test_execute_with_negative_stock_protection(client: TestClient, db: Session, seed_data: dict, mock_provider_env):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_adjustment", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": -10})]),
        ProviderResponse(text="Prepared")
    ])
    
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Adjust TEST01 by -10"})
    action_id = resp1.json()["action_proposals"][0]["action_id"]

    resp2 = client.post(f"/api/v1/copilot/actions/{action_id}/execute")
    assert resp2.status_code == 422
    assert "negative stock" in resp2.json()["detail"]

def test_execute_transfer(client: TestClient, db: Session, seed_data: dict, mock_provider_env):
    client.post(
        "/api/v1/inventory/receipts",
        json={"product_id": str(seed_data["product"].id), "location_id": str(seed_data["loc1"].id), "quantity": "10"}
    )
    
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_transfer", arguments={"product_query": "TEST01", "source_location_query": "Main Store", "destination_location_query": "Godown", "quantity": 4})]),
        ProviderResponse(text="Prepared")
    ])

    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Transfer 4 TEST01"})
    action_id = resp1.json()["action_proposals"][0]["action_id"]

    resp2 = client.post(f"/api/v1/copilot/actions/{action_id}/execute")
    assert resp2.status_code == 200

    bal_src = db.scalar(select(InventoryBalance).where(InventoryBalance.location_id == seed_data["loc1"].id))
    bal_dst = db.scalar(select(InventoryBalance).where(InventoryBalance.location_id == seed_data["loc2"].id))
    assert bal_src.available_quantity == 6
    assert bal_dst.available_quantity == 4

def test_rbac_write_required(client: TestClient, as_principal, mock_provider_env):
    as_principal(role="viewer")
    
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": 10})]),
        ProviderResponse(text="You don't have permission")
    ])
    
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Receive 10 items"})
    assert len(resp1.json()["action_proposals"]) == 0
    assert "permission" in resp1.json()["answer"].lower()

def test_tampered_payload_rejected(client: TestClient):
    resp = client.post(f"/api/v1/copilot/actions/{uuid.uuid4()}/execute")
    assert resp.status_code == 404

def test_cancellation(client: TestClient, seed_data: dict, mock_provider_env):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": 5})]),
        ProviderResponse(text="Prepared")
    ])
    
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Receive 5 units"})
    action_id = resp1.json()["action_proposals"][0]["action_id"]

    resp2 = client.post(f"/api/v1/copilot/actions/{action_id}/cancel")
    assert resp2.status_code == 200
    
    resp3 = client.post(f"/api/v1/copilot/actions/{action_id}/execute")
    assert resp3.status_code == 400


def test_fallback_openrouter_persistence(client: TestClient, db: Session, seed_data: dict, monkeypatch):
    from app.api.v1.routes import copilot
    from app.domain.copilot.provider import ProviderQuotaExceededError
    from app.core.config import get_settings, Settings
    from app.main import app
    
    # 1. Override settings to include OpenRouter API key
    def _mock_settings_with_fallback():
        return Settings(
            gemini_api_key="fake-gemini", 
            gemini_model="gemini",
            openrouter_api_key="fake-or",
            openrouter_model="openrouter"
        )
    app.dependency_overrides[get_settings] = _mock_settings_with_fallback

    # 2. Mock Gemini to succeed on first turn (prepare tool), then fail on second turn
    class FailingGeminiProvider:
        def __init__(self, api_key, model):
            self.call_count = 0
            
        def generate(self, messages, tools):
            if self.call_count == 0:
                self.call_count += 1
                return ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "TEST01", "location_query": "Main Store", "quantity": 10})])
            raise ProviderQuotaExceededError("Gemini Quota Exceeded")
            
    monkeypatch.setattr(copilot, "GoogleGenAIProvider", FailingGeminiProvider)

    # 3. Mock OpenRouter to succeed (this handles the fallback after Gemini fails)
    class MockOpenRouterProvider:
        def __init__(self, api_key, model):
            pass
            
        def generate(self, messages, tools):
            # It should receive the context, including the successful tool call from the first turn!
            assert len(messages) > 2
            assert messages[-1].role == "tool"
            return ProviderResponse(text="Fallback successful: Action prepared!")
            
    monkeypatch.setattr(copilot, "OpenRouterProvider", MockOpenRouterProvider)

    # Execute chat request
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Receive 10 units"})
    assert resp1.status_code == 200
    
    data = resp1.json()
    assert data["answer"] == "Fallback successful: Action prepared!"
    assert len(data["action_proposals"]) == 1
    action_id = data["action_proposals"][0]["action_id"]

    # Verify that the action is persistently retrievable
    resp2 = client.post(f"/api/v1/copilot/actions/{action_id}/execute")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "success"
    
    # Cleanup overrides
    app.dependency_overrides.pop(get_settings, None)


