from __future__ import annotations

import streamlit as st

from src.frontend.app import main

import streamlit as st


params = st.query_params
st.session_state["chat_dev_badge"] = str(params.get("dev", "")).strip().lower() in {"1", "true", "yes", "on"}

if "dev_mode" not in st.session_state:
    st.session_state["dev_mode"] = str(st.query_params.get("dev", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

main(active_page="Chat")
