import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.inventory.models import Product, InventoryLocation, LocationType, Unit
from app.domain.copilot.models import CopilotConversationMessage
from app.domain.copilot.provider import MockProvider, ProviderResponse, ToolCallRequest
from app.api.v1.routes import copilot
from app.core.config import get_settings, Settings
from app.main import app

@pytest.fixture
def seed_data(db: Session):
    org = "org_test_a"
    p = Product(organization_id=org, name="Tata Tea Gold", sku="TATA01", unit=Unit.piece, cost_price=10, selling_price=15, gst_rate=5)
    loc1 = InventoryLocation(organization_id=org, name="Main Shop", location_type=LocationType.store)
    loc2 = InventoryLocation(organization_id=org, name="Godown", location_type=LocationType.warehouse)
    
    db.add_all([p, loc1, loc2])
    db.commit()
    return {"product": p, "loc1": loc1, "loc2": loc2}

@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    from app.domain.copilot import service
    service._GEMINI_COOLDOWN_UNTIL = 0.0

def test_multilingual_inventory_query(client: TestClient, db: Session, mock_provider_env):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="get_inventory_summary", arguments={})]),
        ProviderResponse(text="Aapke paas 100 maal bacha hai.")
    ])
    
    # Hinglish query
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "kitna maal bacha h"})
    assert resp1.status_code == 200
    assert "100" in resp1.json()["answer"]
    assert "maal bacha hai" in resp1.json()["answer"]

def test_multiturn_missing_location_clarification(client: TestClient, db: Session, mock_provider_env, seed_data):
    # Turn 1: User gives incomplete instruction
    mock_provider_env([
        ProviderResponse(text="Kaunsa product bhejna hai?")
    ])
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "10 packet godown bhej do"})
    assert resp1.status_code == 200
    assert "product" in resp1.json()["answer"]
    
    # Verify memory is saved
    msgs = db.scalars(select(CopilotConversationMessage).where(CopilotConversationMessage.user_id == "user_001")).all()
    assert len(msgs) >= 2 # Should have at least the ones from this turn
    
    # Turn 2: User provides missing info
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_transfer", arguments={"product_query": "Tata Tea Gold", "source_location_query": "Main Shop", "destination_location_query": "Godown", "quantity": 10})]),
        ProviderResponse(text="Action prepared.")
    ])
    resp2 = client.post("/api/v1/copilot/chat", json={"message": "Tata Tea Gold main shop se"})
    assert resp2.status_code == 200
    assert len(resp2.json()["action_proposals"]) == 1
    
    proposal = resp2.json()["action_proposals"][0]
    assert proposal["action_type"] == "transfer"
    assert proposal["payload"]["quantity"] == 10

def test_conversation_isolation_between_users(client: TestClient, as_principal, db: Session, mock_provider_env):
    # Create messages for user_a
    msg1 = CopilotConversationMessage(organization_id="org_test_a", user_id="user_a", role="user", content="Secret user A message")
    # Create messages for user_b
    msg2 = CopilotConversationMessage(organization_id="org_test_a", user_id="user_b", role="user", content="Secret user B message")
    db.add_all([msg1, msg2])
    db.commit()
    
    as_principal(user_id="user_b")
    
    class InspectProvider:
        def __init__(self, api_key, model): pass
        def generate(self, messages, tools):
            # Assert user_b is not seeing user_a's message
            content = " ".join(str(m.content) for m in messages)
            assert "Secret user B message" in content
            assert "Secret user A message" not in content
            return ProviderResponse(text="Inspected.")
            
    import app.api.v1.routes.copilot as c
    c.GoogleGenAIProvider = InspectProvider
    
    client.post("/api/v1/copilot/chat", json={"message": "Hello"})

def test_circuit_breaker(client: TestClient, monkeypatch):
    import time
    from app.domain.copilot.provider import ProviderQuotaExceededError
    from app.domain.copilot import service
    
    # Reset circuit breaker
    service._GEMINI_COOLDOWN_UNTIL = 0.0
    
    def _mock_settings():
        return Settings(gemini_api_key="fake", gemini_model="fake", openrouter_api_key="fake-or", openrouter_model="or-model")
    app.dependency_overrides[get_settings] = _mock_settings
    
    class TrippingGemini:
        def __init__(self, *args, **kwargs): pass
        def generate(self, messages, tools):
            raise ProviderQuotaExceededError("Gemini Quota Exceeded")
            
    class WorkingOpenRouter:
        def __init__(self, *args, **kwargs): pass
        def generate(self, messages, tools):
            return ProviderResponse(text="OpenRouter Success")
            
    monkeypatch.setattr(copilot, "GoogleGenAIProvider", TrippingGemini)
    monkeypatch.setattr(copilot, "OpenRouterProvider", WorkingOpenRouter)
    
    # Request 1: hits Gemini, throws 429, falls back to OpenRouter, trips circuit breaker
    r1 = client.post("/api/v1/copilot/chat", json={"message": "test"})
    assert r1.status_code == 200
    assert r1.json()["answer"] == "OpenRouter Success"
    assert service._GEMINI_COOLDOWN_UNTIL > time.time() # tripped
    
    # Let's track if Gemini is even instantiated/called on the second request
    class PanickingGemini:
        def __init__(self, *args, **kwargs): pass
        def generate(self, messages, tools):
            pytest.fail("Gemini was called despite circuit breaker being open!")
            
    monkeypatch.setattr(copilot, "GoogleGenAIProvider", PanickingGemini)
    
    # Request 2: should immediately use OpenRouter
    r2 = client.post("/api/v1/copilot/chat", json={"message": "test 2"})
    assert r2.status_code == 200
    assert r2.json()["answer"] == "OpenRouter Success"
    
    app.dependency_overrides.pop(get_settings, None)

def test_security_text_confirm_does_not_execute(client: TestClient, db: Session, mock_provider_env, seed_data):
    # Turn 1: Copilot prepares the Phase 5B proposal
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "Tata Tea Gold", "location_query": "Main Shop", "quantity": 10})]),
        ProviderResponse(text="Action prepared. Please click Confirm.")
    ])
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "receive 10 Tata Tea Gold to Main Shop"})
    assert resp1.status_code == 200
    assert len(resp1.json()["action_proposals"]) == 1
    
    # Verify balance is zero
    from app.domain.inventory.models import InventoryBalance
    balance_before = db.scalar(select(InventoryBalance.available_quantity).where(InventoryBalance.product_id == seed_data["product"].id))
    assert not balance_before or balance_before == 0
    
    # Turn 2: User types "Confirm" text instead of clicking the button
    mock_provider_env([
        ProviderResponse(text="Sure, but you still need to click the Confirm button.")
    ])
    resp2 = client.post("/api/v1/copilot/chat", json={"message": "Confirm"})
    assert resp2.status_code == 200
    
    # Verify action was NOT executed (balance is still zero)
    balance_after = db.scalar(select(InventoryBalance.available_quantity).where(InventoryBalance.product_id == seed_data["product"].id))
    assert not balance_after or balance_after == 0
