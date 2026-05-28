from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.ai.conversation_orchestrator import get_preferences
from src.backend.services.ai.question_policy import select_next_question
from src.backend.services.ai.chat_llm_orchestrator import ChatOrchestrator, ModelSettings

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
def test_chat_response_includes_policy_decision_fields():
    response = client.post("/chat/message", json={"message": "I am not sure"})
    assert response.status_code == 200
    body = response.json()
    assert body["assistant_action"]
    assert "decision_reason" in body
    assert "decision_confidence" in body


def test_chat_uses_llm_policy_when_policy_orchestrator_valid(monkeypatch):
    from src.backend.api import chat as chat_api

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
            return None
        def update_stage(self, *args, **kwargs):
            return None

    class PolicyClient:
        def __init__(self):
            self.calls = 0
        def generate_json(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return json.dumps({
                    "assistant_action": "ask_follow_up",
                    "target_slot": "transmission",
                    "question_text": "Do you prefer manual or automatic transmission?",
                    "confidence": 0.95,
                    "reason": "missing required slot"
                })
            return json.dumps({
                "reply": "Do you prefer manual or automatic transmission?",
                "confidence": 0.9,
                "assistant_action": "ask_follow_up",
                "follow_up_question": "Do you prefer manual or automatic transmission?",
                "template_used": "follow_up"
            })

    monkeypatch.setattr(chat_api, "SessionsRepository", FakeRepo)
    original = chat_api._orchestrator
    chat_api._orchestrator = ChatOrchestrator(client=PolicyClient(), settings=_test_settings())
    try:
        response = client.post("/chat/message", json={"message": "I need a car"})
    finally:
        chat_api._orchestrator = original

    assert response.status_code == 200
    body = response.json()
    assert body["target_slot"] == "transmission"
    assert body["assistant_action"] == "ask_follow_up"


def test_chat_falls_back_to_deterministic_policy_when_llm_policy_invalid(monkeypatch):
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

    class BadPolicyClient:
        def __init__(self):
            self.calls = 0
        def generate_json(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return json.dumps({
                    "assistant_action": "ask_follow_up",
                    "target_slot": None,
                    "question_text": None,
                    "confidence": 0.95,
                    "reason": "bad schema"
                })
            return json.dumps({
                "reply": "What type of fuel would you prefer for your next vehicle?",
                "confidence": 0.9,
                "assistant_action": "ask_follow_up",
                "follow_up_question": "What type of fuel would you prefer for your next vehicle?",
                "template_used": "follow_up"
            })

    monkeypatch.setattr(chat_api, "SessionsRepository", FakeRepo)
    original = chat_api._orchestrator
    chat_api._orchestrator = ChatOrchestrator(client=BadPolicyClient(), settings=_test_settings())
    try:
        response = client.post("/chat/message", json={"message": "I need a car"})
    finally:
        chat_api._orchestrator = original

    assert response.status_code == 200
    details = events[-1]["details"]
    assert details["policy_source"] == "deterministic"
