import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.domain.inventory.models import Product, InventoryLocation, LocationType, Unit, InventoryBalance
from app.domain.copilot.provider import ProviderResponse, ToolCallRequest

@pytest.fixture
def voice_seed_data(db: Session):
    org = "org_test_a"
    p = Product(organization_id=org, name="Tata Salt", sku="TATA_SALT", unit=Unit.packet, cost_price=10, selling_price=15, gst_rate=5)
    loc = InventoryLocation(organization_id=org, name="Main Shop", location_type=LocationType.store)
    
    db.add_all([p, loc])
    db.commit()
    return {"product": p, "loc": loc}

def test_voice_hindi_inventory_query(client: TestClient, db: Session, mock_provider_env, voice_seed_data):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="lookup_product", arguments={"query": "Tata Salt"})]),
        ProviderResponse(text="Tata Salt ka current stock 0 packets hai.")
    ])
    
    resp = client.post("/api/v1/copilot/chat", json={"message": "Tata Salt kitna bacha hai?"})
    assert resp.status_code == 200
    assert "Tata Salt" in resp.json()["answer"]
    assert "0" in resp.json()["answer"]

def test_voice_hindi_action_preparation(client: TestClient, db: Session, mock_provider_env, voice_seed_data):
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "Tata Salt", "location_query": "Main Shop", "quantity": 10})]),
        ProviderResponse(text="Maine 10 packets Tata Salt receive karne ka setup kar diya hai. Kripya Confirm karein.")
    ])
    
    resp = client.post("/api/v1/copilot/chat", json={"message": "Main shop mein 10 packet Tata Salt receive karo"})
    assert resp.status_code == 200
    proposals = resp.json().get("action_proposals", [])
    assert len(proposals) == 1
    assert proposals[0]["action_type"] == "receipt"
    assert proposals[0]["payload"]["quantity"] == 10
    
    # Inventory remains unchanged!
    balance = db.scalar(select(InventoryBalance.available_quantity).where(InventoryBalance.product_id == voice_seed_data["product"].id))
    assert not balance or balance == 0

@pytest.mark.parametrize("confirmation_phrase", ["haan", "yes", "confirm it", "kar do"])
def test_voice_confirmation_words_do_not_execute(client: TestClient, db: Session, mock_provider_env, voice_seed_data, confirmation_phrase):
    # Turn 1: Prepare the action
    mock_provider_env([
        ProviderResponse(tool_calls=[ToolCallRequest(name="prepare_stock_receipt", arguments={"product_query": "Tata Salt", "location_query": "Main Shop", "quantity": 10})]),
        ProviderResponse(text="Action prepared.")
    ])
    resp1 = client.post("/api/v1/copilot/chat", json={"message": "Main shop mein 10 packet Tata Salt receive karo"})
    assert len(resp1.json()["action_proposals"]) == 1
    
    # Turn 2: User says a confirmation word
    mock_provider_env([
        ProviderResponse(text="You must click the confirm button to proceed.")
    ])
    resp2 = client.post("/api/v1/copilot/chat", json={"message": confirmation_phrase})
    assert resp2.status_code == 200
    
    # Inventory MUST remain 0, meaning action did not execute
    balance = db.scalar(select(InventoryBalance.available_quantity).where(InventoryBalance.product_id == voice_seed_data["product"].id))
    assert not balance or balance == 0
