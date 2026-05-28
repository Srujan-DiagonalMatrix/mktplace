from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass, field
from typing import Any


class _Context:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    def __init__(self):
        self.session_state: dict[str, Any] = {}
        self.markdown_calls: list[str] = []
        self.info_calls: list[str] = []
        self.button_calls: list[tuple[str, dict[str, Any]]] = []
        self.text_input_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.button_results: dict[str, bool] = {}
        self.text_input_value = ""

    def markdown(self, body: str, **_kwargs):
        self.markdown_calls.append(body)

    def info(self, body: str):
        self.info_calls.append(body)

    def container(self):
        return _Context()

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Context() for _ in range(count)]

    def button(self, label: str, **kwargs):
        self.button_calls.append((label, kwargs))
        key = kwargs.get("key", label)
        return self.button_results.get(key, False)

    def text_input(self, *args, **kwargs):
        self.text_input_calls.append((args, kwargs))
        return self.text_input_value


@dataclass
class _Response:
    payload: Any = field(default_factory=dict)

    def json(self):
        return self.payload


def _install_fake_streamlit(monkeypatch) -> _FakeStreamlit:
    fake_st = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    return fake_st


def _reload_module(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def _install_fake_settings(monkeypatch, host: str = "api.local", port: int = 9000):
    fake_settings_module = types.ModuleType("src.shared.config.settings")
    fake_settings_module.get_settings = lambda: types.SimpleNamespace(
        fastapi_host=host,
        fastapi_port=port,
    )
    monkeypatch.setitem(sys.modules, "src.shared.config.settings", fake_settings_module)


def test_session_state_creates_preferences_and_resets(monkeypatch):
    fake_st = _install_fake_streamlit(monkeypatch)
    module = _reload_module("src.frontend.state.session_state")

    session_id = module.get_session_id()
    module.set_preferences({"monthly_budget": 500})
    module.set_preferences({"fuel_type": "Hybrid"})

    assert session_id == "sess-0"
    assert fake_st.session_state["session_id"] == "sess-0"
    assert module.get_preferences() == {"monthly_budget": 500, "fuel_type": "Hybrid"}

    module.reset_session_state()

    assert "session_id" not in fake_st.session_state
    assert "preferences" not in fake_st.session_state


def test_chat_panel_send_message_uses_mock_backend_and_updates_preferences(monkeypatch):
    fake_st = _install_fake_streamlit(monkeypatch)
    _install_fake_settings(monkeypatch)
    fake_requests = types.SimpleNamespace(
        get=lambda *args, **kwargs: _Response({}),
        post=lambda *args, **kwargs: _Response({}),
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    sys.modules.pop("src.frontend.api_client.client", None)
    sys.modules.pop("src.frontend.state.session_state", None)
    module = _reload_module("src.frontend.components.chat_panel")

    class Backend:
        def __init__(self):
            self.payloads: list[dict[str, Any]] = []

        def post_chat(self, payload):
            self.payloads.append(payload)
            return {"preferences": {"monthly_budget": 475, "fuel_type": "Petrol"}}

    backend = Backend()

    module._send_message("Around 475 a month", "sess-chat", backend_client=backend)

    assert backend.payloads == [
        {"session_id": "sess-chat", "message": "Around 475 a month"}
    ]
    assert fake_st.session_state["preferences"] == {
        "monthly_budget": 475,
        "fuel_type": "Petrol",
    }
    assert fake_st.session_state["chat_messages"][-2]["role"] == "user"
    assert fake_st.session_state["chat_messages"][-1]["role"] == "ai"


def test_chat_panel_renders_without_calling_backend_when_no_input(monkeypatch):
    fake_st = _install_fake_streamlit(monkeypatch)
    _install_fake_settings(monkeypatch)
    fake_requests = types.SimpleNamespace(
        get=lambda *args, **kwargs: _Response({}),
        post=lambda *args, **kwargs: _Response({}),
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    sys.modules.pop("src.frontend.api_client.client", None)
    sys.modules.pop("src.frontend.state.session_state", None)
    module = _reload_module("src.frontend.components.chat_panel")

    def fake_start_chat(_payload):
        return {"reply": "Backend greeting"}

    def fail_post_chat(_payload):
        raise AssertionError("chat_panel should not call /chat/message unless the user sends input")

    monkeypatch.setattr(module.client, "start_chat", fake_start_chat)
    monkeypatch.setattr(module.client, "post_chat", fail_post_chat)

    module.chat_panel()

    rendered = "\n".join(fake_st.markdown_calls)
    assert "Conversation" in rendered
    assert "Backend greeting" in rendered
    assert fake_st.button_calls[-1][0] == "➤"


def test_recommendation_cards_render_content_and_empty_state(monkeypatch):
    fake_st = _install_fake_streamlit(monkeypatch)
    module = _reload_module("src.frontend.components.recommendation_cards")

    module.render_recommendation_cards(
        [
            {
                "make": "Tesla",
                "model": "Model 3",
                "variant": "Long Range",
                "fuel_type": "Electric",
                "transmission": "Automatic",
                "seats": 5,
                "pricing": {"monthly_from_gbp": 449},
                "image": "assets/cars/model-3.png",
            }
        ]
    )

    rendered = "\n".join(fake_st.markdown_calls)
    assert "Top Recommendations" in rendered
    assert "Tesla Model 3" in rendered
    assert "£449/mo" in rendered
    assert "Best Match" in rendered
    assert [label for label, _kwargs in fake_st.button_calls] == [
        "View Details",
        "Shortlist",
        "Enquire",
    ]

    fake_st.markdown_calls.clear()
    fake_st.info_calls.clear()
    fake_st.button_calls.clear()
    module.render_recommendation_cards([])

    empty_rendered = "\n".join(fake_st.markdown_calls + fake_st.info_calls)
    assert "No recommendations yet" in empty_rendered
    assert "chat with the assistant" in empty_rendered.lower()
    assert fake_st.button_calls == []


def test_summary_cards_use_session_state_and_defaults(monkeypatch):
    fake_st = _install_fake_streamlit(monkeypatch)
    fake_st.session_state.update(
        {
            "preferences": {"monthly_budget": 625},
            "finance_term": 48,
            "finance_deposit": 1500,
        }
    )
    module = _reload_module("src.frontend.components.summary_cards")

    module.summary_cards(monthly_budget=500, term_months=36, deposit=0)

    rendered = "\n".join(fake_st.markdown_calls)
    assert "£625 Monthly Budget" in rendered
    assert "48 Months Term" in rendered
    assert "£1500 Initial Deposit" in rendered

    fake_st.session_state.clear()
    fake_st.markdown_calls.clear()
    module.summary_cards()

    defaults_rendered = "\n".join(fake_st.markdown_calls)
    assert "£0 Monthly Budget" in defaults_rendered
    assert "36 Months Term" in defaults_rendered
    assert "£0 Initial Deposit" in defaults_rendered


def test_finance_summary_formats_values(monkeypatch):
    fake_st = _install_fake_streamlit(monkeypatch)
    module = _reload_module("src.frontend.components.finance_summary")

    module.finance_summary(monthly_budget=1250, term_months=24, deposit=3500)

    rendered = "\n".join(fake_st.markdown_calls)
    assert "Finance Summary" in rendered
    assert "£1,250" in rendered
    assert "24 months" in rendered
    assert "£3,500" in rendered
    assert "View Finance Options" in rendered


def test_backend_client_builds_base_url_from_settings(monkeypatch):
    _install_fake_settings(monkeypatch, host="backend.internal", port=8123)
    fake_requests = types.SimpleNamespace(get=lambda *args, **kwargs: _Response({}))
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    module = _reload_module("src.frontend.api_client.client")

    client = module.BackendClient()

    assert client.base == "http://backend.internal:8123"


def test_backend_client_post_chat_calls_chat_endpoint(monkeypatch):
    calls: list[tuple[str, dict[str, Any]]] = []
    fake_requests = types.SimpleNamespace()

    def fake_post(url, json):
        calls.append((url, json))
        return _Response({"ok": True})

    fake_requests.post = fake_post
    fake_requests.get = lambda *args, **kwargs: _Response({})
    _install_fake_settings(monkeypatch)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    module = _reload_module("src.frontend.api_client.client")

    response = module.BackendClient(base_url="http://backend.test").post_chat(
        {"message": "hello"}
    )

    assert response == {"ok": True}
    assert calls == [("http://backend.test/chat/message", {"message": "hello"})]


def test_backend_client_start_chat_calls_start_endpoint(monkeypatch):
    calls: list[tuple[str, dict[str, Any]]] = []
    fake_requests = types.SimpleNamespace()

    def fake_post(url, json):
        calls.append((url, json))
        return _Response({"reply": "Welcome"})

    fake_requests.post = fake_post
    fake_requests.get = lambda *args, **kwargs: _Response({})
    _install_fake_settings(monkeypatch)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    module = _reload_module("src.frontend.api_client.client")

    response = module.BackendClient(base_url="http://backend.test").start_chat(
        {"session_id": "sess-1"}
    )

    assert response == {"reply": "Welcome"}
    assert calls == [("http://backend.test/chat/start", {"session_id": "sess-1"})]


def test_backend_client_get_recommendations_includes_session_id(monkeypatch):
    calls: list[tuple[str, dict[str, Any]]] = []
    fake_requests = types.SimpleNamespace()

    def fake_get(url, params=None):
        calls.append((url, params or {}))
        return _Response([{"vehicle_id": "veh-1"}])

    fake_requests.get = fake_get
    fake_requests.post = lambda *args, **kwargs: _Response({})
    _install_fake_settings(monkeypatch)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    module = _reload_module("src.frontend.api_client.client")

    response = module.BackendClient(base_url="http://backend.test").get_recommendations(
        session_id="sess-123"
    )

    assert response == [{"vehicle_id": "veh-1"}]
    assert calls == [
        (
            "http://backend.test/recommendations/from_session",
            {"limit": 3, "session_id": "sess-123"},
        )
    ]


def test_backend_client_create_enquiry_calls_enquiries_endpoint(monkeypatch):
    calls: list[tuple[str, dict[str, Any]]] = []
    expected_response = _Response({"id": "enq-1"})
    fake_requests = types.SimpleNamespace()

    def fake_post(url, json):
        calls.append((url, json))
        return expected_response

    fake_requests.post = fake_post
    fake_requests.get = lambda *args, **kwargs: _Response({})
    _install_fake_settings(monkeypatch)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    module = _reload_module("src.frontend.api_client.client")
    payload = {"vehicle_id": "veh-1", "full_name": "Ada"}

    response = module.BackendClient(base_url="http://backend.test").create_enquiry(
        payload
    )

    assert response is expected_response
    assert calls == [("http://backend.test/enquiries/", payload)]
