from __future__ import annotations

from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.ai.conversation_orchestrator import get_preferences

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


def test_chat_response_includes_policy_decision_fields():
    response = client.post("/chat/message", json={"message": "I am not sure"})
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_action"]
    assert "decision_reason" in body
    assert "decision_confidence" in body
