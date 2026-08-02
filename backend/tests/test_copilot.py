import pytest
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.copilot.provider import MockProvider, ProviderResponse, ToolCallRequest
from app.api.v1.routes.copilot import copilot_chat
from app.domain.inventory.models import Product, Unit, InventoryLocation, LocationType, InventoryBalance

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(setup_db):
    session = TestingSessionLocal()
    yield session
    session.close()

def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)

def test_copilot_unauthenticated(db_session):
    # Missing Authorization header
    response = client.post("/api/v1/copilot/chat", json={"message": "hello"})
    assert response.status_code == 401

# We will need to mock the authentication and the config
from app.core.auth import get_principal, Principal
from app.core.config import get_settings

def _mock_principal_a(): return Principal(organization_id="org_a", user_id="user_1", role="admin")
def _mock_principal_b(): return Principal(organization_id="org_b", user_id="user_2", role="admin")

def _mock_config():
    from app.core.config import Settings
    return Settings(gemini_api_key="fake", gemini_model="fake-model")

@pytest.fixture
def seed_data(db_session):
    u = uuid.uuid4().hex
    p1 = Product(organization_id="org_a", name=f"Tata Tea {u}", sku=f"TT1_{u}", unit=Unit.piece, cost_price=10, selling_price=12, gst_rate=5)
    p2 = Product(organization_id="org_b", name=f"Tata Tea {u}", sku=f"TT2_{u}", unit=Unit.piece, cost_price=10, selling_price=12, gst_rate=5)
    
    loc1 = InventoryLocation(organization_id="org_a", name=f"Main_{u}", location_type=LocationType.store)
    loc2 = InventoryLocation(organization_id="org_b", name=f"Main_{u}", location_type=LocationType.store)
    
    db_session.add_all([p1, p2, loc1, loc2])
    db_session.commit()
    
    b1 = InventoryBalance(organization_id="org_a", product_id=p1.id, location_id=loc1.id, available_quantity=100)
    b2 = InventoryBalance(organization_id="org_b", product_id=p2.id, location_id=loc2.id, available_quantity=50)
    
    db_session.add_all([b1, b2])
    db_session.commit()
    
    return {"p1": p1, "p2": p2}

def test_tenant_isolation_product_lookup(seed_data, monkeypatch):
    # We want to test the orchestration without hitting real API.
    # The endpoint instantiates CopilotService directly with GoogleGenAIProvider.
    # We'll monkeypatch GoogleGenAIProvider to return a MockProvider instance.
    
    from app.api.v1.routes import copilot
    
    # We want the LLM to request lookup_product with "Tata Tea"
    mock_responses = [
        ProviderResponse(
            tool_calls=[ToolCallRequest(name="lookup_product", arguments={"query": "Tata Tea"})]
        ),
        ProviderResponse(text="Found the tea!")
    ]
    
    def _fake_provider(api_key, model):
        return MockProvider(mock_responses)
        
    monkeypatch.setattr(copilot, "GoogleGenAIProvider", _fake_provider)
    
    app.dependency_overrides[get_principal] = _mock_principal_a
    app.dependency_overrides[get_settings] = _mock_config
    
    response = client.post("/api/v1/copilot/chat", json={"message": "How much Tata Tea?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Found the tea!"
    assert "lookup_product" in data["tools_used"]
    
    # We can check what tool got injected by using a more direct unit test
    
def test_copilot_service_isolation_unit(db_session, seed_data):
    from app.domain.copilot.service import CopilotService
    
    # Simulate Org A
    mock_provider = MockProvider([
        ProviderResponse(tool_calls=[ToolCallRequest(name="lookup_product", arguments={"query": "Tata Tea"})]),
        ProviderResponse(text="Done")
    ])
    
    service = CopilotService(provider=mock_provider, db=db_session, principal=_mock_principal_a())
    # Instead of full chat, we can just test the tool execution directly:
    res_str = service._execute_tool(ToolCallRequest(name="lookup_product", arguments={"query": "Tata Tea"}))
    assert '"available_quantity": "100.000"' in res_str
    assert '"available_quantity": "50.000"' not in res_str # Should not see org B's 50 units

    # Simulate Org B
    service_b = CopilotService(provider=mock_provider, db=db_session, principal=_mock_principal_b())
    res_str_b = service_b._execute_tool(ToolCallRequest(name="lookup_product", arguments={"query": "Tata Tea"}))
    assert '"available_quantity": "50.000"' in res_str_b
    assert '"available_quantity": "100.000"' not in res_str_b

def test_copilot_service_unapproved_tool(db_session):
    from app.domain.copilot.service import CopilotService
    service = CopilotService(provider=MockProvider([]), db=db_session, principal=_mock_principal_a())
    
    res = service._execute_tool(ToolCallRequest(name="delete_all_data", arguments={}))
    assert "error" in res
    assert "is not allowed" in res
    
def test_copilot_service_invalid_args(db_session):
    from app.domain.copilot.service import CopilotService
    service = CopilotService(provider=MockProvider([]), db=db_session, principal=_mock_principal_a())
    
    res = service._execute_tool(ToolCallRequest(name="lookup_product", arguments={})) # missing query
    assert "error" in res
    assert "Invalid arguments" in res

def test_copilot_service_loop_limit(db_session):
    from app.domain.copilot.service import CopilotService
    
    # Provide infinite tool calls
    infinite_responses = [
        ProviderResponse(tool_calls=[ToolCallRequest(name="get_inventory_summary", arguments={})])
    ] * 10
    
    mock_provider = MockProvider(infinite_responses)
    service = CopilotService(provider=mock_provider, db=db_session, principal=_mock_principal_a())
    
    res = service.handle_chat("Summarize inventory")
    assert "max tool calls reached" in res.answer
    assert len(res.tools_used) == 5 # hit max loop of 5

def test_provider_failure(db_session, monkeypatch):
    from app.domain.copilot.service import CopilotService
    from app.api.v1.routes import copilot
    
    class FailingProvider:
        def generate(self, messages, tools):
            raise RuntimeError("API quota exceeded")
            
    monkeypatch.setattr(copilot, "GoogleGenAIProvider", lambda api_key, model: FailingProvider())
    app.dependency_overrides[get_principal] = _mock_principal_a
    app.dependency_overrides[get_settings] = _mock_config
    
    response = client.post("/api/v1/copilot/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert "trouble connecting to my AI brain" in response.json()["answer"]
