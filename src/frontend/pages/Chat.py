from __future__ import annotations

import streamlit as st

from src.frontend.app import main


if "dev_mode" not in st.session_state:
    st.session_state["dev_mode"] = str(st.query_params.get("dev", "")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

main(active_page="Chat")
