from __future__ import annotations

from html import escape

import streamlit as st

NAV_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("Chat", "💬", "/Chat"),
    ("Recommendations", "✨", "/Recommendations"),
    ("Finance", "💳", "/Finance"),
    ("Shortlist", "♡", "/Shortlist"),
    ("Admin", "⚙️", "/Settings"),
)


def _nav_item_html(label: str, icon: str, route: str, active: str) -> str:
    is_active = label == active
    classes = "nav-item active" if is_active else "nav-item"
    aria_current = ' aria-current="page"' if is_active else ""
    return (
        f'<a class="nav-link" href="{escape(route)}" target="_self">'
        f'<div class="{classes}"{aria_current}>'
        f"<span>{escape(icon)}</span>{escape(label)}"
        "</div></a>"
    )


def _sidebar_nav_html(active: str) -> str:
    nav_items = "\n".join(
        _nav_item_html(label=label, icon=icon, route=route, active=active)
        for label, icon, route in NAV_ITEMS
    )
    return f"""
    <aside class="glass-card nav-card" aria-label="Primary navigation">
      <div class="logo-tile">🚗</div>
      <nav class="nav-stack">
        {nav_items}
      </nav>
    </aside>
    """


def sidebar_nav(active: str = "Chat") -> None:
    """Render the static sidebar navigation for the Streamlit app."""
    st.markdown(_sidebar_nav_html(active=active), unsafe_allow_html=True)
