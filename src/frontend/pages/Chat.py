from __future__ import annotations

from src.frontend.app import main

import streamlit as st


params = st.query_params
st.session_state["chat_dev_badge"] = str(params.get("dev", "")).strip().lower() in {"1", "true", "yes", "on"}

main(active_page="Chat")
