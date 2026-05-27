from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.ai.conversation_orchestrator import get_preferences
from src.backend.services.ai.chat_llm_orchestrator import ChatOrchestrator, ModelSettings

client = TestClient(app)


def test_chat_budget_response_includes_budget_session_and_reply():
    response = client.post("/chat/message", json={"message": "budget £500 per month"})

    assert response.status_code == 200
    body = response.json()
    assert body["monthly_budget"] == 500
    assert body["session_id"]
    assert body["reply"]


def test_chat_fuel_preference_updates_existing_session_preferences():
    budget_response = client.post("/chat/message", json={"message": "budget £500 per month"})
    session_id = budget_response.json()["session_id"]

    response = client.post(
        "/chat/message",
        json={"session_id": session_id, "message": "I prefer diesel"},
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == session_id
    assert response.json()["fuel_type"] == "Diesel"
    assert get_preferences(session_id)["monthly_budget"] == 500
    assert get_preferences(session_id)["fuel_type"] == "Diesel"


def test_recommendations_from_session_reads_chat_preferences(monkeypatch):
    class FakeCatalog:
        vehicles = {}
        pricing = {}

    captured = {}

    def fake_apply_filters(vehicles, pricing, prefs):
        captured["prefs"] = dict(prefs)
        return []

    monkeypatch.setattr("src.backend.api.recommendations.get_catalog", lambda: FakeCatalog())
    monkeypatch.setattr("src.backend.api.recommendations.apply_filters", fake_apply_filters)

    chat_response = client.post("/chat/message", json={"message": "budget £500 per month"})
    session_id = chat_response.json()["session_id"]
    client.post(
        "/chat/message",
        json={"session_id": session_id, "message": "I prefer petrol"},
    )

    response = client.get("/recommendations/from_session", params={"session_id": session_id})

    assert response.status_code == 200
    assert captured["prefs"]["monthly_budget"] == 500
    assert captured["prefs"]["fuel_type"] == "Petrol"


def _test_settings() -> ModelSettings:
    return ModelSettings(
        version="test-v1",
        model="test-model",
        temperature=0.1,
        max_output_tokens=100,
        confidence_threshold=0.6,
        max_reply_chars=50,
    )


def test_chat_logs_fallback_diagnostics_when_api_key_absent(monkeypatch):
    from src.backend.api import chat as chat_api

    events = []

    class FakeRepo:
        def __init__(self, db):
            pass

        def get_session(self, session_id):
            return {"session_id": session_id}

        def create_session(self, **kwargs):
            return None

        def create_turn(self, **kwargs):
            class _Turn:
                turn_id = "turn-1"
            return _Turn()

        def create_preference_snapshot(self, **kwargs):
            return None

        def log_event(self, **kwargs):
            events.append(kwargs)
            return None

        def update_stage(self, *args, **kwargs):
            return None

    monkeypatch.setattr(chat_api, "SessionsRepository", FakeRepo)
    original = chat_api._orchestrator
    chat_api._orchestrator = ChatOrchestrator(client=None, settings=_test_settings())
    try:
        response = client.post("/chat/message", json={"message": "I need a car"})
    finally:
        chat_api._orchestrator = original

    assert response.status_code == 200
    details = events[-1]["details"]
    assert details["used_llm"] is False
    assert details["fallback_reason"] == "missing_api_key"
    assert details["model_name"] == "test-model"
    assert details["decision_source"] == "deterministic"


def test_chat_logs_fallback_diagnostics_when_structured_parse_fails(monkeypatch):
    from src.backend.api import chat as chat_api

    events = []

    class FakeRepo:
        def __init__(self, db):
            pass

        def get_session(self, session_id):
            return {"session_id": session_id}

        def create_session(self, **kwargs):
            return None

        def create_turn(self, **kwargs):
            class _Turn:
                turn_id = "turn-1"
            return _Turn()

        def create_preference_snapshot(self, **kwargs):
            return None

        def log_event(self, **kwargs):
            events.append(kwargs)
            return None

        def update_stage(self, *args, **kwargs):
            return None

    class BrokenClient:
        def generate_json(self, **kwargs):
            return "not json"

    monkeypatch.setattr(chat_api, "SessionsRepository", FakeRepo)
    original = chat_api._orchestrator
    chat_api._orchestrator = ChatOrchestrator(client=BrokenClient(), settings=_test_settings())
    try:
        response = client.post("/chat/message", json={"message": "Need help"})
    finally:
        chat_api._orchestrator = original

    assert response.status_code == 200
    details = events[-1]["details"]
    assert details["used_llm"] is False
    assert details["fallback_reason"] == "model_error"
    assert details["model_name"] == "test-model"
    assert details["decision_source"] == "deterministic"
