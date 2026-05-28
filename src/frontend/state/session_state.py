from __future__ import annotations

import streamlit as st


RESET_SESSION_STATE_KEYS = (
    "session_id",
    "chat_messages",
    "preferences",
    "selected_vehicle",
    "selected_vehicle_obj",
    "finance_term",
    "finance_deposit",
    "chat_bootstrap_loaded",
)


def reset_session_state(keys: tuple[str, ...] | list[str] | None = None) -> None:
    """Remove session-scoped UI state so a new buying conversation can start."""
    for key in keys or RESET_SESSION_STATE_KEYS:
        st.session_state.pop(key, None)


def get_session_id() -> str:
    if "session_id" not in st.session_state:
        next_index = int(st.session_state.get("_session_seq", 0))
        st.session_state["_session_seq"] = next_index + 1
        st.session_state["session_id"] = f"sess-{next_index}"
    return st.session_state["session_id"]


def set_preferences(prefs: dict) -> None:
    st.session_state.setdefault("preferences", {}).update(prefs)
    if prefs.get("deposit_gbp") is not None:
        st.session_state["finance_deposit"] = prefs["deposit_gbp"]
    if prefs.get("term_months") is not None:
        st.session_state["finance_term"] = prefs["term_months"]


def get_preferences() -> dict:
    return st.session_state.get("preferences", {})
