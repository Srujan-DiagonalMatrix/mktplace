from __future__ import annotations

import json

import pytest

from src.backend.services.ai.chat_llm_orchestrator import (
    ChatOrchestrator,
    ModelSettings,
    PromptTemplate,
    FallbackReason,
)


from src.shared.config.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class FakeClient:
    def __init__(self, payload: dict | None = None, error: Exception | None = None):
        self.payload = payload
        self.error = error

    def generate_json(self, **kwargs):
        if self.error:
            raise self.error
        return json.dumps(self.payload)


def _settings() -> ModelSettings:
    return ModelSettings(
        version="test-v1",
        model="test-model",
        temperature=0.1,
        max_output_tokens=100,
        confidence_threshold=0.6,
        max_reply_chars=50,
    )


def test_orchestrator_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    payload = {
        "reply": "Great, I can help narrow this down for you.",
        "confidence": 0.9,
        "follow_up_question": "Do you prefer petrol or diesel?",
        "template_used": "follow_up",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())
    out = orch.run(session={"messages": ["hi"], "preferences": {}}, user_message="need a car", template=PromptTemplate.FOLLOW_UP)
    assert out.used_llm is True
    assert out.response is not None
    assert out.response.reply


def test_orchestrator_timeout_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    orch = ChatOrchestrator(client=FakeClient(error=TimeoutError("timeout")), settings=_settings())
    out = orch.run(session={"messages": [], "preferences": {}}, user_message="hello", template=PromptTemplate.GREETING)
    assert out.used_llm is False
    assert out.fallback_reason == FallbackReason.MODEL_ERROR


def test_orchestrator_low_confidence_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    payload = {"reply": "maybe", "confidence": 0.2, "follow_up_question": None, "template_used": "clarification"}
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())
    out = orch.run(session={"messages": [], "preferences": {}}, user_message="idk", template=PromptTemplate.CLARIFICATION)
    assert out.fallback_reason == FallbackReason.LOW_CONFIDENCE


def test_orchestrator_guardrail_blocks_fabricated_claims(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    payload = {
        "reply": "I can give legal advice and guaranteed approval.",
        "confidence": 0.95,
        "follow_up_question": None,
        "template_used": "handoff_summary",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())
    out = orch.run(session={"messages": [], "preferences": {}}, user_message="help", template=PromptTemplate.HANDOFF_SUMMARY)
    assert out.fallback_reason == FallbackReason.GUARDRAIL_BLOCK


def test_prompt_assembly_uses_session_memory(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    orch = ChatOrchestrator(client=FakeClient({"reply": "ok", "confidence": 0.9, "follow_up_question": None, "template_used": "greeting"}), settings=_settings())
    prompt = orch.build_prompt(
        session={"messages": ["m1", "m2"], "preferences": {"fuel_type": "Petrol"}},
        user_message="hello",
        template=PromptTemplate.GREETING,
    )
    assert "fuel_type" in prompt
    assert "m1" in prompt
    assert "Prompt config version: test-v1" in prompt


def test_orchestrator_missing_key_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    orch = ChatOrchestrator(client=None, settings=_settings())
    out = orch.run(session={"messages": [], "preferences": {}}, user_message="hello", template=PromptTemplate.GREETING)
    assert out.fallback_reason == FallbackReason.MISSING_API_KEY


class SpyClient:
    def __init__(self, payload: dict):
        self.payload = payload
        self.calls: list[dict] = []

    def generate_json(self, **kwargs):
        self.calls.append(kwargs)
        return json.dumps(self.payload)


def test_default_model_setting_is_gpt_5_4_nano(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.delenv("OPENAI_CHAT_MODEL", raising=False)
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    orch = ChatOrchestrator(client=FakeClient({"reply": "ok", "confidence": 0.9, "follow_up_question": None, "template_used": "greeting"}))

    assert orch._settings.model == "gpt-5.4-nano"


def test_explicit_model_override_is_respected(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-5.4")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    orch = ChatOrchestrator(client=FakeClient({"reply": "ok", "confidence": 0.9, "follow_up_question": None, "template_used": "greeting"}))

    assert orch._settings.model == "gpt-5.4"


def test_orchestrator_passes_resolved_model_to_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    spy = SpyClient({"reply": "ok", "confidence": 0.9, "follow_up_question": None, "template_used": "greeting"})
    orch = ChatOrchestrator(client=spy)

    out = orch.run(session={"messages": [], "preferences": {}}, user_message="hello", template=PromptTemplate.GREETING)

    assert out.used_llm is True
    assert spy.calls
    assert spy.calls[0]["model"] == "gpt-5.4-mini"


def test_policy_orchestrator_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    payload = {
        "assistant_action": "ask_follow_up",
        "target_slot": "fuel_type",
        "question_text": "What fuel type do you prefer?",
        "confidence": 0.95,
        "reason": "required slot missing",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())
    out = orch.run_policy_orchestrator(session={"messages": ["hi"], "preferences": {}}, user_message="need a car")
    assert out.used_llm is True
    assert out.response is not None
    assert out.response.target_slot == "fuel_type"


def test_policy_orchestrator_falls_back_on_low_confidence(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    payload = {
        "assistant_action": "ask_follow_up",
        "target_slot": "fuel_type",
        "question_text": "What fuel type do you prefer?",
        "confidence": 0.2,
        "reason": "unsure",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())
    out = orch.run_policy_orchestrator(session={"messages": [], "preferences": {}}, user_message="idk")
    assert out.used_llm is False
    assert out.fallback_reason == FallbackReason.LOW_CONFIDENCE


def test_prompt_assembly_includes_curated_exemplars(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    (tmp_path / "conversation_turns.jsonl").write_text(
        '{"message":"hello","preferences":{},"hesitation_count":0,"expected_action":"ask_follow_up","expected_next_slot":"fuel_type"}\n',
        encoding="utf-8",
    )
    from src.backend.services.ai.curated_runtime_adapter import CuratedInteractionAdapter
    orch = ChatOrchestrator(
        client=FakeClient({"reply": "ok", "confidence": 0.9, "follow_up_question": None, "template_used": "greeting"}),
        settings=_settings(),
        curated_adapter=CuratedInteractionAdapter(base_dir=tmp_path),
    )
    prompt = orch.build_prompt(
        session={"messages": ["m1"], "preferences": {"hesitation_count": 0}},
        user_message="hello",
        template=PromptTemplate.GREETING,
        few_shot_exemplars=orch._curated_adapter.get_few_shot_exemplars(preferences={}, hesitation_count=0),
    )
    assert "Curated few-shot exemplars" in prompt
    assert "expected_next_slot" in prompt


def test_orchestrator_accepts_terminal_summary_actions_in_strict_mode(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("LLM_POLICY_MODE", "strict")
    payload = {
        "reply": "Great — I’ll show your recommendations now.",
        "confidence": 0.95,
        "assistant_action": "present_recommendations",
        "follow_up_question": None,
        "follow_up_slot_tag": None,
        "template_used": "follow_up",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())

    out = orch.run(
        session={"messages": ["Yes, show recommendations"], "preferences": {"summary_presented": True}},
        user_message="Yes, show recommendations",
        template=PromptTemplate.FOLLOW_UP,
        policy_decision={"assistant_action": "present_recommendations", "target_slot": None},
    )

    assert out.used_llm is True
    assert out.response is not None
    assert out.response.assistant_action == "present_recommendations"
    assert out.response.follow_up_question is None


def test_policy_orchestrator_accepts_present_recommendations_terminal_action(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    payload = {
        "assistant_action": "present_recommendations",
        "target_slot": None,
        "question_text": None,
        "confidence": 0.95,
        "reason": "summary confirmed",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())

    out = orch.run_policy_orchestrator(
        session={"messages": ["Yes, show recommendations"], "preferences": {"summary_presented": True}},
        user_message="Yes, show recommendations",
    )

    assert out.used_llm is True
    assert out.response is not None
    assert out.response.assistant_action == "present_recommendations"
    assert out.response.target_slot is None


def test_policy_orchestrator_rejects_terminal_action_with_question(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    payload = {
        "assistant_action": "present_recommendations",
        "target_slot": "transmission",
        "question_text": "Do you prefer automatic?",
        "confidence": 0.95,
        "reason": "invalid terminal payload",
    }
    orch = ChatOrchestrator(client=FakeClient(payload), settings=_settings())

    out = orch.run_policy_orchestrator(
        session={"messages": [], "preferences": {"summary_presented": True}},
        user_message="Yes",
    )

    assert out.used_llm is False
    assert out.fallback_reason == FallbackReason.POLICY_MISMATCH
