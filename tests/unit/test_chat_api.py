from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.ai.conversation_orchestrator import get_preferences
from src.backend.services.ai.question_policy import select_next_question

client = TestClient(app)

TURN_FIXTURES = Path("data/interaction/conversation_turns.jsonl")
POLICY_LABELS = Path("dialogue_policy_labels.jsonl")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def test_dialogue_policy_alignment_and_progression_thresholds():
    turns = {row["turn_id"]: row for row in _load_jsonl(TURN_FIXTURES)}
    labels = _load_jsonl(POLICY_LABELS)

    aligned = 0
    clarifications = 0
    repeated_risk = 0
    summarize_or_recommend = 0

    for row in labels:
        turn = turns[row["turn_id"]]
        spec = select_next_question(
            turn.get("preferences", {}),
            asked_keys=turn.get("asked_keys", []),
            user_message=turn["message"],
            hesitation_count=turn.get("hesitation_count", 0),
        )
        actual_slot = spec.key if spec else "none"
        if actual_slot == row["expected_slot"]:
            aligned += 1
        if actual_slot == "clarification":
            clarifications += 1
        if actual_slot in set(turn.get("asked_keys", [])) and actual_slot != "clarification":
            repeated_risk += 1
        if row["expected_policy"] == "summarize_or_recommend" and actual_slot == "none":
            summarize_or_recommend += 1

    alignment_score = aligned / len(labels)
    clarification_rate = clarifications / sum(1 for t in turns.values() if t["is_uncertain"])

    assert alignment_score >= 0.85
    assert clarification_rate >= 0.65
    assert repeated_risk == 0
    assert summarize_or_recommend >= 1
