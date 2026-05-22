from __future__ import annotations

import importlib
import sys
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
        self.button_calls: list[str] = []

    def markdown(self, body: str, **_kwargs):
        self.markdown_calls.append(body)

    def info(self, body: str):
        self.info_calls.append(body)

    def header(self, *_args, **_kwargs):
        return None

    def subheader(self, *_args, **_kwargs):
        return None

    def write(self, *_args, **_kwargs):
        return None

    def image(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def success(self, *_args, **_kwargs):
        return None

    def container(self):
        return _Context()

    def columns(self, spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_Context() for _ in range(count)]

    def button(self, label: str, **_kwargs):
        self.button_calls.append(label)
        return False


def _reload(module: str):
    sys.modules.pop(module, None)
    return importlib.import_module(module)


def test_recommendation_cards_smoke(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    module = _reload("src.frontend.components.recommendation_cards")

    module.render_recommendation_cards([])

    rendered = "\n".join(fake_st.markdown_calls + fake_st.info_calls)
    assert "No recommendations yet" in rendered


def test_summary_cards_smoke(monkeypatch):
    fake_st = _FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)
    module = _reload("src.frontend.components.summary_cards")

    module.summary_cards(monthly_budget=500, term_months=36, deposit=0)

    rendered = "\n".join(fake_st.markdown_calls)
    assert "Monthly Budget" in rendered
    assert "Months Term" in rendered
