from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st


def _normalize_top_pain_points(payload: dict[str, Any]) -> list[dict[str, Any]]:
    points = payload.get("top_pain_points", []) or []
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(points[:5], start=1):
        label = str(item.get("label", "unknown")).replace("_", " ").title()
        normalized.append(
            {
                "rank": idx,
                "pain_area": label,
                "weight": int(item.get("frequency", 0)),
                "confidence": round(float(item.get("max_confidence", 0.0)), 2),
            }
        )
    return normalized


def _infer_icp_mix(payload: dict[str, Any]) -> list[dict[str, Any]]:
    sessions = payload.get("session_drilldown", []) or []
    buckets = {"Family": 0, "Student": 0, "Business": 0, "Couple": 0, "Large Family": 0, "Low Income": 0}
    for session in sessions:
        pain_points = [str(x).lower() for x in session.get("pain_points", [])]
        turns = int(session.get("turns", 0))
        if "family_size" in pain_points or turns > 10:
            buckets["Family"] += 1
        elif "budget" in pain_points or "financing" in pain_points:
            buckets["Low Income"] += 1
        elif "commercial" in pain_points:
            buckets["Business"] += 1
        elif turns <= 4:
            buckets["Student"] += 1
        else:
            buckets["Couple"] += 1
    return [{"profile": k, "sessions": v} for k, v in buckets.items() if v > 0]


def _build_interaction_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in payload.get("session_drilldown", []) or []:
        pain_list = s.get("pain_points") or []
        rows.append(
            {
                "interaction_id": s.get("session_id"),
                "date": str(date.today()),
                "time": "--:--",
                "duration_min": int(s.get("turns", 0)) * 2,
                "top_pain_area": pain_list[0].replace("_", " ").title() if pain_list else "N/A",
                "icp_primary": "Inferred",
                "conversation_score": round(float(s.get("sentiment", 0.0)), 2),
            }
        )
    return rows


def _build_conversation_history_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in payload.get("session_drilldown", []) or []:
        pain_list = [str(p).replace("_", " ").title() for p in (s.get("pain_points") or [])]
        sentiment = float(s.get("sentiment", 0.0))
        seriousness = "High" if sentiment < -0.25 else "Medium" if sentiment < 0.15 else "Low"
        rows.append(
            {
                "interaction_id": s.get("session_id", "unknown"),
                "date_of_interaction": str(date.today()),
                "time_of_interaction": "--:--",
                "customer_name": s.get("customer_name", "Prospect"),
                "contact_details": s.get("contact", "not_provided@example.com"),
                "channel": s.get("channel", "chat"),
                "summary_of_interaction": s.get("summary", "Customer discussed vehicle preferences and constraints."),
                "top_5_pain_points": ", ".join(pain_list[:5]) if pain_list else "N/A",
                "weights": int(s.get("turns", 0)),
                "seriousness_to_proceed": seriousness,
                "icp_primary": s.get("icp_primary", "Inferred"),
                "conversation_duration_min": int(s.get("turns", 0)) * 2,
                "assigned_manager": s.get("owner", "Unassigned"),
                "status": s.get("status", "open"),
                "view": "View",
            }
        )
    return rows


def render_analytics_dashboard(client: Any) -> None:
    # Step 1 from plan: reset legacy admin fields and show redesigned admin IA.
    st.subheader("Admin Intelligence Console")
    st.caption("Redesigned admin tab with conversation summary, weighted pain areas, ICP mix, interaction explorer, and reporting visuals.")

    filters = st.container(border=True)
    with filters:
        c1, c2, c3 = st.columns(3)
        start = c1.date_input("Start date", value=None)
        end = c2.date_input("End date", value=None)
        stage = c3.selectbox("Session stage", ["all", "awareness", "consideration", "decision"])

    payload = client.get_analytics_dashboard(
        start_date=str(start) if start else None,
        end_date=str(end) if end else None,
        stage=None if stage == "all" else stage,
    )

    kpis = payload.get("kpis", {})
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Interactions", kpis.get("sessions", 0))
    k2.metric("Negative sentiment days", kpis.get("top_negative_sentiment_days", 0))
    k3.metric("Drop-off total", kpis.get("dropoff_total", 0))
    k4.metric("Unique pain points", kpis.get("unique_pain_points", 0))

    st.markdown("### 1) Summary of Conversation")
    st.info(
        "This summary is generated from the selected date range and stage filters. "
        "Use interaction details to inspect full transcript and metadata."
    )

    st.markdown("### 2) Top 5 Pain Point Weights")
    top_pains = _normalize_top_pain_points(payload)
    if top_pains:
        st.dataframe(top_pains, use_container_width=True, hide_index=True)
    else:
        st.warning("No weighted pain points available for current filters.")

    st.markdown("### 3) Ideal Customer Profile (Inferred Mix)")
    icp_mix = _infer_icp_mix(payload)
    if icp_mix:
        st.bar_chart(icp_mix, x="profile", y="sessions")
    else:
        st.warning("No ICP segments available for current filters.")

    st.markdown("### 4) Interactions Table")
    rows = _build_interaction_rows(payload)
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        selected = st.selectbox("View interaction details", [r["interaction_id"] for r in rows])
        st.json({"interaction_id": selected, "meta": "Detailed transcript and metadata integration point."})
    else:
        st.warning("No interactions found for current filters.")

    st.markdown("### 5) Conversation History")
    history_rows = _build_conversation_history_rows(payload)
    if history_rows:
        st.dataframe(history_rows, use_container_width=True, hide_index=True)
        selected_interaction = st.selectbox(
            "Select interaction row to view details",
            [r["interaction_id"] for r in history_rows],
            key="conversation_history_view",
        )
        st.button("View", key="conversation_history_view_btn")
        st.json(
            {
                "interaction_id": selected_interaction,
                "report": "Detailed conversation report placeholder with transcript and metadata.",
            }
        )
    else:
        st.warning("No conversation history available for current filters.")

    st.markdown("### 6) Dashboard Reports")
    trend_rows = payload.get("sentiment_trends", {})
    if trend_rows:
        chart_rows = [{"date": d, **vals} for d, vals in trend_rows.items()]
        st.line_chart(chart_rows, x="date", y=["positive", "neutral", "negative"])
    else:
        st.info("No trend data available.")
