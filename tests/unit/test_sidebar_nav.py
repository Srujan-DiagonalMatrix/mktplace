from __future__ import annotations

import importlib
import sys
import types


streamlit_stub = types.SimpleNamespace(markdown=lambda *args, **kwargs: None)
sys.modules.setdefault("streamlit", streamlit_stub)

sidebar_nav_module = importlib.import_module("src.frontend.components.sidebar_nav")
NAV_ITEMS = sidebar_nav_module.NAV_ITEMS
sidebar_nav = sidebar_nav_module.sidebar_nav


def test_sidebar_nav_renders_all_menu_items(monkeypatch):
    rendered: list[tuple[str, bool]] = []

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        rendered.append((body, unsafe_allow_html))

    monkeypatch.setattr(sidebar_nav_module.st, "markdown", fake_markdown)

    sidebar_nav()

    assert rendered
    body, unsafe = rendered[0]
    assert unsafe is True
    for label, icon in NAV_ITEMS:
        assert label in body
        assert icon in body


def test_sidebar_nav_marks_requested_active_item(monkeypatch):
    rendered: list[str] = []

    def fake_markdown(body: str, unsafe_allow_html: bool = False) -> None:
        rendered.append(body)

    monkeypatch.setattr(sidebar_nav_module.st, "markdown", fake_markdown)

    sidebar_nav(active="Finance")

    body = rendered[0]
    assert 'href="/Finance"' in body
    assert '<div class="nav-item active" aria-current="page"><span>💳</span>Finance</div>' in body
    assert '<div class="nav-item active" aria-current="page"><span>💬</span>Chat</div>' not in body
