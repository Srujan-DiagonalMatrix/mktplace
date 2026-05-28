from __future__ import annotations

import importlib
import sys
import types

import pytest


class _FakeContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit(types.SimpleNamespace):
    def __init__(self):
        super().__init__()
        self.session_state = {}

    def markdown(self, *args, **kwargs):
        return None

    def container(self):
        return _FakeContext()

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_FakeContext() for _ in range(count)]

    def button(self, *args, **kwargs):
        return False

    def text_input(self, *args, **kwargs):
        return ""


class _FakeBackendClient:
    def start_chat(self, payload):
        return {"reply": "Backend hello"}

    def post_chat(self, payload):
        return {}


@pytest.fixture()
def chat_panel_module(monkeypatch):
    fake_st = _FakeStreamlit()
    fake_client_module = types.ModuleType("src.frontend.api_client.client")
    fake_client_module.BackendClient = lambda: _FakeBackendClient()

    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    monkeypatch.setitem(sys.modules, "src.frontend.api_client.client", fake_client_module)
    sys.modules.pop("src.frontend.state.session_state", None)
    sys.modules.pop("src.frontend.components.chat_panel", None)

    module = importlib.import_module("src.frontend.components.chat_panel")
    module.st.session_state.clear()
    return module


def test_initial_messages_exist(chat_panel_module):
    chat_panel_module._ensure_messages()

    messages = chat_panel_module.st.session_state["chat_messages"]
    assert [message["role"] for message in messages] == ["ai"]
    assert [message["text"] for message in messages] == ["Backend hello"]
    assert all("time" in message for message in messages)


def test_initial_message_stores_bootstrap_metadata(chat_panel_module):
    class Backend:
        def start_chat(self, payload):
            return {
                "reply": "What fuel type do you prefer?",
                "assistant_action": "ask_preference",
                "target_slot": "fuel_type",
                "question_metadata": {"options": ["Petrol", "Hybrid"]},
            }

    chat_panel_module._ensure_messages(session_id="sess-1", backend_client=Backend())
    message = chat_panel_module.st.session_state["chat_messages"][0]
    assert message["assistant_action"] == "ask_preference"
    assert message["target_slot"] == "fuel_type"
    assert message["question_metadata"] == {"options": ["Petrol", "Hybrid"]}


def test_initial_message_uses_local_fallback_when_backend_unavailable(chat_panel_module):
    class Backend:
        def start_chat(self, payload):
            raise RuntimeError("down")

    message = chat_panel_module._bootstrap_message("sess-1", backend_client=Backend())
    assert message["text"] == chat_panel_module.FALLBACK_GREETING


def test_send_budget_appends_user_message(chat_panel_module):
    class Backend:
        def post_chat(self, payload):
            return {"monthly_budget": 450}

    chat_panel_module._send_message("$450 per month", "sess-1", backend_client=Backend())

    messages = chat_panel_module.st.session_state["chat_messages"]
    assert any(
        message["role"] == "user" and message["text"] == "$450 per month"
        for message in messages
    )


def test_post_chat_preferences_are_written_to_state(chat_panel_module):
    class Backend:
        def post_chat(self, payload):
            return {"preferences": {"monthly_budget": 500, "fuel_type": "Petrol"}}

    chat_panel_module._send_message("Budget is 500 and petrol", "sess-1", backend_client=Backend())

    assert chat_panel_module.st.session_state["preferences"] == {
        "monthly_budget": 500,
        "fuel_type": "Petrol",
    }


def test_send_message_uses_backend_reply_and_quick_replies(chat_panel_module):
    class Backend:
        def post_chat(self, payload):
            return {"reply": "What body type do you want?", "quick_replies": ["SUV", "Hatchback"]}

    chat_panel_module._send_message("My budget is 500", "sess-1", backend_client=Backend())
    last_message = chat_panel_module.st.session_state["chat_messages"][-1]
    assert last_message["role"] == "ai"
    assert last_message["text"] == "What body type do you want?"
    assert last_message["quick_replies"] == ["SUV", "Hatchback"]


def test_quick_reply_uses_send_message_logic(chat_panel_module, monkeypatch):
    calls = []

    def fake_send_message(txt, session_id=None):
        calls.append((txt, session_id))

    monkeypatch.setattr(chat_panel_module, "_send_message", fake_send_message)

    chat_panel_module._send_quick_reply("Hybrid / Electric", "sess-quick")

    assert calls == [("Hybrid / Electric", "sess-quick")]


def test_present_recommendations_action_does_not_append_summary_prompt(chat_panel_module):
    reply_text, quick_replies = chat_panel_module._apply_assistant_action(
        "Great — I’ll show your recommendations now.",
        {"assistant_action": "present_recommendations"},
    )

    assert reply_text == "Great — I’ll show your recommendations now."
    assert "Would you like me to continue" not in reply_text
    assert quick_replies is None
