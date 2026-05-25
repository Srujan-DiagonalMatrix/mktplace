from __future__ import annotations

import streamlit as st
from src.frontend.api_client.client import BackendClient
from src.frontend.components.chat_panel import chat_panel
from src.frontend.components.recommendation_cards import render_recommendation_cards
from src.frontend.components.sidebar_nav import sidebar_nav
from src.frontend.components.car_detail import car_detail
from src.frontend.components.enquiry_form import enquiry_form
from src.frontend.components.finance_summary import finance_summary
from src.frontend.components.header import render_header
from src.frontend.components.analytics_dashboard import render_analytics_dashboard
from src.frontend.components.summary_cards import summary_cards
from src.frontend.state.session_state import get_preferences, get_session_id

client = BackendClient()

PAGE_CSS = """
<style>
:root {
  --sky: #0b7cff;
  --sky-50: #eff7ff;
  --sky-100: #dceeff;
  --sky-200: #c8e0ff;
  --border: rgba(159, 201, 255, 0.62);
  --ink: #0f172a;
  --muted: #5b6f93;
  --shadow: 0 24px 70px rgba(37, 99, 235, 0.13);
  --soft-shadow: 0 16px 42px rgba(15, 23, 42, 0.08);
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  min-height: 100vh;
  background:
    radial-gradient(circle at 12% 10%, rgba(126, 200, 255, 0.38), transparent 32%),
    linear-gradient(135deg, #e4f4ff 0%, #f7fbff 48%, #ffffff 100%);
}

.block-container {
  max-width: none;
  padding: 1.25rem 1.5rem 0.9rem;
}

[data-testid="stHeader"], [data-testid="stToolbar"] {
  background: transparent;
}


[data-testid="stSidebar"] {
  display: none;
}

[data-testid="stVerticalBlock"] { gap: 0.85rem; }

button[kind="secondary"], .stButton > button {
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.88);
  color: var(--sky);
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.08);
}

button[kind="secondary"]:hover, .stButton > button:hover {
  border-color: var(--sky);
  color: var(--sky);
  background: #ffffff;
}

input, textarea {
  border-radius: 14px !important;
  border-color: var(--border) !important;
}

[data-testid="column"] {
  align-self: stretch;
}

[data-testid="column"] > div {
  height: 100%;
}

[data-testid="column"] [data-testid="stVerticalBlock"] {
  align-content: flex-start;
}

.glass-card {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid var(--border);
  border-radius: 30px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}

.nav-card {
  min-height: calc(100vh - 3rem);
  padding: 1.15rem 1rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-tile {
  width: min(112px, 100%);
  height: auto;
  aspect-ratio: 1 / 1;
  border-radius: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  align-self: center;
  color: white;
  font-size: 2.2rem;
  background: linear-gradient(145deg, #0b7cff, #6bbdff);
  box-shadow: 0 14px 28px rgba(11, 124, 255, 0.28);
  margin: 0.65rem auto 1.8rem;
}

.nav-stack {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  width: 100%;
}

.nav-link,
.nav-link:hover,
.nav-link:focus,
.nav-link:visited,
.nav-link * {
  text-decoration: none !important;
}

.nav-item {
  min-height: 104px;
  border-radius: 24px;
  color: #4c5c7d;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1;
}

.nav-icon { font-size: 2.05rem; }

.nav-label {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.nav-item.active {
  background: linear-gradient(180deg, #f3f9ff, #e8f4ff);
  border: 2px solid #2f78ff;
  color: #1458d8;
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.12);
}

.chat-region, .recommendation-region {
  min-height: calc(100vh - 3rem);
  display: flex;
  flex-direction: column;
}

.title-card {
  padding: 1.25rem 1.35rem;
  margin-bottom: 1rem;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.title-copy h1 {
  margin: 0;
  color: var(--ink);
  font-size: clamp(1.9rem, 2.4vw, 2.75rem);
  line-height: 1.08;
  letter-spacing: -0.04em;
}

.title-copy p {
  margin: 0.45rem 0 0;
  color: var(--muted);
  font-size: 0.98rem;
}

.chat-card {
  padding: 1.25rem;
  flex: 1;
  height: calc(100vh - 3rem);
  overflow: hidden;
}

.chat-scroll-frame {
  height: 360px;
  min-height: 360px;
  max-height: 360px;
  overflow-y: auto;
  padding-right: 0.25rem;
  scroll-behavior: smooth;
}

.recommendation-card {
  padding: 1.25rem;
  flex: 1;
}

.panel-kicker {
  color: var(--sky);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 0.25rem;
}

.panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel-heading h2 {
  margin: 0;
  color: var(--ink);
  font-size: 1.35rem;
}

.panel-heading p {
  margin: 0.25rem 0 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.status-pill {
  border: 1px solid #bfddff;
  background: rgba(239, 247, 255, 0.82);
  color: #2368c4;
  padding: 0.45rem 0.7rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
  white-space: nowrap;
}

.msg-ai {
  max-width: 88%;
  background: linear-gradient(180deg, #f7fbff 0%, #ecf6ff 100%);
  border: 1px solid #dceeff;
  border-radius: 20px;
  padding: 0.95rem;
  color: var(--ink);
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 0.8rem;
  display: flex;
  gap: 0.75rem;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.06);
}

.msg-user {
  margin-left: auto;
  background: linear-gradient(135deg, #ddf0ff 0%, #b9dcff 100%);
  border-radius: 20px;
  padding: 0.85rem 1rem;
  color: #075bb5;
  font-weight: 700;
  max-width: 80%;
  margin-bottom: 0.8rem;
}

.ai-avatar {
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(145deg, #0b7cff, #6bbdff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 1rem;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(140px, 1fr));
  gap: 0.85rem;
  margin-bottom: 1rem;
}

.summary-small {
  background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(239,247,255,0.92));
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 0.9rem;
  min-height: 78px;
  box-shadow: var(--soft-shadow);
}

.car-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(190px, 1fr));
  gap: 1rem;
  margin-top: 0.9rem;
}

.car-card {
  background: rgba(255,255,255,0.9);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 1rem;
  min-height: 380px;
  box-shadow: var(--soft-shadow);
  transition: transform .18s ease, box-shadow .18s ease;
}

.car-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 22px 44px rgba(37, 99, 235, 0.14);
}

.prototype-car-card {
  background: #ffffff;
  border: 1px solid #dbe7ff;
  border-radius: 28px;
  padding: 1.35rem;
  box-shadow: 0 18px 42px rgba(20, 85, 255, 0.1);
}

.prototype-image-wrap {
  position: relative;
  border-radius: 22px;
  background: linear-gradient(180deg, #f4f9ff 0%, #edf4ff 100%);
  padding: 0.45rem;
  margin-bottom: 1rem;
}

.prototype-image-wrap img {
  width: 100%;
  height: 210px;
  object-fit: contain;
  border-radius: 18px;
  display: block;
}

.prototype-heart {
  position: absolute;
  right: 12px;
  top: 12px;
  color: #64748b;
  font-size: 1.1rem;
}

.prototype-title {
  margin: 0 0 0.4rem;
  color: #0f2a5f;
  font-size: clamp(1.35rem, 1.95vw, 1.65rem);
  font-weight: 800;
  line-height: 1.2;
}

.prototype-subtitle {
  margin: 0 0 0.85rem;
  color: #526580;
  font-size: 0.92rem;
}

.prototype-specs {
  display: flex;
  gap: 0.85rem;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 0.95rem;
}

.prototype-spec {
  color: #526580;
  font-size: 0.88rem;
}

.prototype-divider {
  width: 1px;
  height: 14px;
  background: #d6e3fb;
}

.prototype-kicker {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.prototype-price {
  margin: 0.3rem 0 0.95rem;
  color: #1455ff;
  font-size: clamp(1.8rem, 3vw, 2.15rem);
  font-weight: 800;
  line-height: 1.05;
}

.prototype-action-row {
  display: flex;
  gap: 0.7rem;
}

.prototype-action-row [data-testid="stHorizontalBlock"] {
  gap: 0.7rem;
}

.prototype-action-row .stButton > button {
  min-height: 52px;
  border-radius: 16px;
  border: 1px solid #1455ff;
  background: #ffffff;
  color: #1455ff;
  font-weight: 800;
}

.car-img {
  width: 100%;
  height: 150px;
  object-fit: contain;
  background: linear-gradient(180deg, #ffffff, #f5fbff);
  border-radius: 18px;
  margin-bottom: 1rem;
}

.badge {
  background: #d7faf0;
  color: #0e9f6e;
  border-radius: 999px;
  padding: 0.38rem 0.65rem;
  font-size: 0.68rem;
  font-weight: 800;
  display: inline-block;
}

.heart { color: #64748b; }
.heart:hover { color: var(--sky); }

.recommendation-region .stButton > button {
  min-height: 2.4rem;
  padding: 0.45rem 0.7rem;
  font-size: 0.8rem;
  border-radius: 12px;
  font-weight: 700;
}

.recommendation-region [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(1) .stButton > button {
  background: #DBEAFE;
  border-color: #BFDBFE;
  color: #1D4ED8;
}

.recommendation-region [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) .stButton > button {
  background: #DCFCE7;
  border-color: #BBF7D0;
  color: #166534;
}

.recommendation-region [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) .stButton > button {
  background: #FEE2E2;
  border-color: #FECACA;
  color: #991B1B;
}

.finance-summary {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid var(--border);
  background: linear-gradient(90deg, rgba(244,250,255,0.95), rgba(255,255,255,0.95));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  box-shadow: var(--soft-shadow);
}

.finance-summary__icon {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #0b7cff, #6bbdff);
  color: #fff;
  font-size: 1.35rem;
  box-shadow: 0 12px 24px rgba(11, 124, 255, 0.2);
}

.finance-summary__content {
  flex: 1;
  min-width: 0;
}

.finance-summary__label {
  color: var(--ink);
  font-size: 1rem;
  font-weight: 800;
}

.finance-summary__copy p {
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.2rem 0 0.75rem;
}

.finance-summary__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(110px, 1fr));
  gap: 0.65rem;
}

.finance-summary__metric span, .safety-note {
  color: var(--muted);
  font-size: 0.82rem;
}

.finance-summary__metric strong {
  color: var(--ink);
  display: block;
  font-size: 1rem;
  margin-top: 0.15rem;
}

.finance-summary__button {
  background: linear-gradient(145deg, #0b7cff, #5fb7ff);
  color: #fff !important;
  border: 0;
  padding: 0.75rem 1rem;
  border-radius: 999px;
  font-weight: 800;
  box-shadow: 0 12px 24px rgba(11, 124, 255, 0.22);
  white-space: nowrap;
}

.safety-note {
  text-align: center;
  padding: 0.75rem 1rem 0;
}

@media (max-width: 1180px) {
  .car-grid { grid-template-columns: repeat(2, minmax(190px, 1fr)); }
  .summary-cards { grid-template-columns: 1fr; }
}

@media (max-width: 900px) {
  .prototype-car-card {
    padding: 1.05rem;
    border-radius: 22px;
  }
  .prototype-image-wrap {
    border-radius: 18px;
  }
  .prototype-image-wrap img {
    height: 182px;
    border-radius: 14px;
  }
  .prototype-title {
    font-size: 1.22rem;
  }
  .prototype-specs {
    gap: 0.6rem;
  }
  .prototype-divider {
    height: 11px;
  }
}

@media (max-width: 640px) {
  .prototype-action-row [data-testid="stHorizontalBlock"] {
    flex-direction: column;
  }
}
</style>
"""


def _render_page_css() -> None:
    st.markdown(PAGE_CSS, unsafe_allow_html=True)


def _render_title_card() -> None:
    render_header()


def _normalise_recommendations(raw_recs: object) -> list[dict]:
    if isinstance(raw_recs, list):
        return [item for item in raw_recs if isinstance(item, dict)]
    if isinstance(raw_recs, dict):
        for key in ("recommendations", "results", "vehicles", "items"):
            value = raw_recs.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _load_recommendations(session_id: str) -> tuple[list[dict], bool]:
    try:
        raw_recs = client.get_recommendations(session_id=session_id)
    except Exception:
        return [], False
    return _normalise_recommendations(raw_recs), True


def _render_chat_panel() -> None:
    st.markdown(
        """
        <div class="panel-heading">
          <div>
            <div class="panel-kicker">Assistant chat</div>
            <h2>Conversation</h2>
            <p>Tell us about your budget, lifestyle, fuel preference, and must-have features.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    chat_panel()


def _render_recommendations_panel(session_id: str) -> None:
    prefs = get_preferences()
    budget = prefs.get("monthly_budget")
    term = st.session_state.get("finance_term", 36)
    deposit = st.session_state.get("finance_deposit", 0)
    recs, backend_available = _load_recommendations(session_id)
    status = "Live recommendations" if backend_available else "Offline preview"

    st.markdown(
        f"""
        <div class="panel-heading">
          <div>
            <div class="panel-kicker">Recommendations</div>
            <h2>Top Recommendations</h2>
            <p>Based on your preferences and finance profile.</p>
          </div>
          <div class="status-pill">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    summary_cards(monthly_budget=budget, term_months=term, deposit=deposit)
    if not backend_available:
        st.info(
            "Backend is not connected yet, so this page is showing the base UI. "
            "Start the API to load personalised vehicles."
        )
    render_recommendation_cards(recs[:3], variant="top3", session_id=session_id, client=client)
    finance_summary(budget, term, deposit)


def _render_safety_footer() -> None:
    st.markdown(
        """
        <footer class="safety-note">
          🔒 Your data is secure, used only to improve your car search,
          and never shared with third parties.
        </footer>
        """,
        unsafe_allow_html=True,
    )




def _render_empty_page(active_page: str) -> None:
    nav_col, content_col = st.columns([0.62, 8.2], gap="large")
    with nav_col:
        sidebar_nav(active=active_page)
    with content_col:
        st.markdown('<div class="glass-card" style="min-height: calc(100vh - 3rem);"></div>', unsafe_allow_html=True)

def main(active_page: str = "Chat", configure_page: bool = True):
    if configure_page:
        st.set_page_config(page_title=f"{active_page} · AI Car Buying Assistant", layout="wide")
    _render_page_css()

    if active_page in {"Deals", "Finance", "Shortlist"}:
        _render_empty_page(active_page)
        _render_safety_footer()
        return

    if active_page == "Admin":
        nav_col, admin_col = st.columns([0.62, 8.2], gap="large")
        with nav_col:
            sidebar_nav(active=active_page)
        with admin_col:
            render_analytics_dashboard(client)
        _render_safety_footer()
        return

    session_id = get_session_id()

    nav_col, chat_col, rec_col = st.columns([0.62, 2.8, 5.4], gap="large")
    with nav_col:
        sidebar_nav(active=active_page)
    with chat_col:
        _render_title_card()
        _render_chat_panel()
    with rec_col:
        _render_recommendations_panel(session_id)

    selected_vehicle = st.session_state.get("selected_vehicle_obj")
    if selected_vehicle:
        car_detail(selected_vehicle)
    if st.session_state.get("selected_vehicle"):
        enquiry_form(default_vehicle_id=st.session_state.get("selected_vehicle"))

    _render_safety_footer()


if __name__ == "__main__":
    main()
