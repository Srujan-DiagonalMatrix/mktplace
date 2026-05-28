from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st



def _normalize_top_pain_points(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate((payload.get('top_pain_points') or [])[:5], start=1):
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                'rank': idx,
                'label': item.get('label', f'Pain Point {idx}'),
                'frequency': int(item.get('frequency', 0) or 0),
                'max_confidence': float(item.get('max_confidence', 0) or 0),
            }
        )
    return rows


def _infer_icp_mix(payload: dict[str, Any]) -> list[dict[str, Any]]:
    drilldown = payload.get('session_drilldown') or []
    family = 0
    student = 0
    for session in drilldown:
        if not isinstance(session, dict):
            continue
        turns = int(session.get('turns', 0) or 0)
        pain_points = set(session.get('pain_points') or [])
        if turns >= 8 or {'family_size', 'safety', 'space'} & pain_points:
            family += 1
        else:
            student += 1
    return [
        {'profile': 'Family', 'count': family},
        {'profile': 'Student', 'count': student},
    ]


def _build_interaction_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in payload.get('session_drilldown') or []:
        if not isinstance(session, dict):
            continue
        turns = int(session.get('turns', 0) or 0)
        rows.append(
            {
                'interaction_id': session.get('session_id', 'unknown'),
                'duration_min': max(turns * 2, 0),
                'pain_points': ', '.join(session.get('pain_points') or []),
                'sentiment': float(session.get('sentiment', 0) or 0),
            }
        )
    return rows


def _build_conversation_history_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in payload.get('session_drilldown') or []:
        if not isinstance(session, dict):
            continue
        turns = int(session.get('turns', 0) or 0)
        pain_points = list(session.get('pain_points') or [])[:5]
        seriousness = 'High' if turns >= 6 else 'Medium' if turns >= 3 else 'Low'
        rows.append(
            {
                'interaction_id': session.get('session_id', 'unknown'),
                'date_of_interaction': date.today().isoformat(),
                'time_of_interaction': '10:00',
                'customer_name': 'Anonymous',
                'contact_details': 'N/A',
                'channel': 'Chat',
                'summary_of_interaction': session.get('summary', ''),
                'top_5_pain_points': ', '.join(pain_points),
                'weights': ', '.join(['1.0'] * len(pain_points)) if pain_points else 'N/A',
                'seriousness_to_proceed': seriousness,
                'icp_primary': 'Family' if turns >= 6 else 'Student',
                'conversation_duration_min': turns * 2,
                'assigned_manager': 'Unassigned',
                'status': 'Open',
                'view': 'View',
            }
        )
    return rows

def transform_sentiment_trends(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for day, sentiments in payload.get('sentiment_trends', {}).items():
        rows.append({'date': day, **sentiments})
    return rows


def _date_range(start: date, periods: int) -> list[str]:
    return [(start + timedelta(days=i)).isoformat() for i in range(periods)]


def _build_demo_dataframe(payload: dict[str, Any], days: int = 30) -> pd.DataFrame:
    base = payload.get('trend_rows') or []
    if base:
        return pd.DataFrame(base)

    dates = _date_range(date.today() - timedelta(days=days - 1), days)
    rows = []
    for idx, day in enumerate(dates):
        sessions = 120 + (idx % 7) * 8 + (idx // 5)
        enquiries = int(sessions * 0.36)
        conversions = int(enquiries * 0.28)
        dropoffs = int(sessions * 0.17)
        sentiment_score = 60 + (idx % 10)
        intent_score = 52 + (idx % 14)
        rows.append(
            {
                'date': day,
                'sessions': sessions,
                'enquiries': enquiries,
                'conversions': conversions,
                'dropoffs': dropoffs,
                'avg_duration_seconds': 145 + (idx % 20) * 3,
                'sentiment_score': sentiment_score,
                'intent_score': intent_score,
            }
        )
    return pd.DataFrame(rows)


def _render_theme() -> None:
    st.markdown(
        """
        <style>
          .stApp { background: #F5F7FB; }
          .insights-header h1 { margin:0; font-size: 2rem; font-weight: 700; color:#0B1F4D; }
          .insights-header p { margin:.2rem 0 0; color:#475569; font-size:1rem; }
          .filter-pill { background:#fff; border:1px solid #E5EAF2; border-radius:12px; padding:10px 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_cards(df: pd.DataFrame) -> None:
    total_sessions = int(df['sessions'].sum())
    total_enquiries = int(df['enquiries'].sum())
    total_conversions = int(df['conversions'].sum())
    total_dropoffs = int(df['dropoffs'].sum())
    avg_duration = float(df['avg_duration_seconds'].mean())
    conversion_rate = (total_conversions / total_enquiries * 100) if total_enquiries else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric('Total conversations', f'{total_sessions:,}')
    c2.metric('Enquiries', f'{total_enquiries:,}')
    c3.metric('Conversions', f'{total_conversions:,}', delta=f'{conversion_rate:.1f}% rate')
    c4.metric('Callbacks', f"{max(total_conversions // 3, 1):,}")
    c5.metric('Drop-offs', f'{total_dropoffs:,}')
    c6.metric('Avg duration', f'{avg_duration:.0f}s')


def _render_section(title: str) -> None:
    st.markdown(f"### {title}")


def _load_dashboard_payload(client: Any, start: date, end: date) -> dict[str, Any]:
    try:
        payload = client.get_analytics_dashboard(
            start_date=str(start) if start else None,
            end_date=str(end) if end else None,
            vehicle_type=None,
            fuel_type=None,
            stage=None,
        )
        return payload if isinstance(payload, dict) else {}
    except Exception:
        st.warning('Analytics backend is unavailable. Showing demo insights.')
        return {}


def _render_filters(start: date, end: date) -> None:
    c1, c2, c3, c4, c5 = st.columns([2.1, 1.2, 1.2, 1.2, 1])
    c1.markdown(f"<div class='filter-pill'><b>Date Range</b><br>{start.strftime('%b %d, %Y')} – {end.strftime('%b %d, %Y')}</div>", unsafe_allow_html=True)
    c2.markdown("<div class='filter-pill'><b>Channel</b><br>All</div>", unsafe_allow_html=True)
    c3.markdown("<div class='filter-pill'><b>Region</b><br>All</div>", unsafe_allow_html=True)
    c4.markdown("<div class='filter-pill'><b>Vehicle</b><br>All</div>", unsafe_allow_html=True)
    c5.button('Refresh', use_container_width=True)


def render_analytics_dashboard(client: Any) -> None:
    _render_theme()
    st.markdown('<div class="insights-header"><h1>Analytics Dashboard</h1><p>Executive Insights</p></div>', unsafe_allow_html=True)

    start = date.today() - timedelta(days=29)
    end = date.today()
    _render_filters(start, end)

    payload = _load_dashboard_payload(client, start, end)
    trend_df = _build_demo_dataframe(payload)

    _kpi_cards(trend_df)

    _render_section('1. Conversation & Conversion')
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.line_chart(trend_df, x='date', y=['sessions', 'enquiries', 'conversions'], use_container_width=True)
    r1c2.area_chart(trend_df, x='date', y=['dropoffs'], use_container_width=True)

    funnel = pd.DataFrame({'stage': ['Conversation started', 'Converted', 'Enquiry submitted', 'Shortlisted'], 'count': [int(trend_df['sessions'].sum()), int(trend_df['conversions'].sum()), int(trend_df['enquiries'].sum()), int(trend_df['enquiries'].sum() * 0.45)]}).set_index('stage')
    r1c3.bar_chart(funnel, horizontal=True, use_container_width=True)
    channel_df = pd.DataFrame({'channel': ['Chat', 'Phone', 'Web', 'WhatsApp'], 'Enquiry rate': [60, 44, 63, 55], 'Drop-off rate': [25, 33, 24, 29], 'Conversion rate': [15, 23, 13, 16]}).set_index('channel')
    r1c4.bar_chart(channel_df, use_container_width=True)

    _render_section('2. Sentiment, Intent & Themes')
    r2c1, r2c2, r2c3 = st.columns(3)
    sentiment = pd.DataFrame({'sentiment': ['Negative', 'Neutral', 'Positive'], 'count': [14, 34, 52]}).set_index('sentiment')
    r2c1.bar_chart(sentiment, use_container_width=True)
    r2c2.line_chart(trend_df, x='date', y=['intent_score'], use_container_width=True)
    themes = pd.DataFrame({'theme': ['Availability', 'Features', 'Finance', 'Pricing', 'Trade-in'], 'frequency': [115, 90, 98, 110, 65]}).set_index('theme')
    r2c3.bar_chart(themes, horizontal=True, use_container_width=True)

    _render_section('3. Vehicle, Finance & AI Operations')
    r3c1, r3c2, r3c3 = st.columns(3)
    top_cars = pd.DataFrame({'car': ['BMW iX1', 'Hyundai Tucson', 'Kia EV6', 'Tesla Model Y', 'Toyota RAV4'], 'shortlists': [60, 45, 50, 55, 40], 'views': [240, 210, 240, 240, 180]}).set_index('car')
    r3c1.bar_chart(top_cars[['shortlists', 'views']], horizontal=True, use_container_width=True)
    finance = pd.DataFrame({'category': ['Need Advice', 'Not Ready', 'Ready'], 'count': [38, 18, 45]}).set_index('category')
    r3c2.bar_chart(finance, use_container_width=True)
    ai_df = pd.DataFrame({'date': trend_df['date'], 'api_cost_estimate': [620 + (i % 8) * 25 for i in range(len(trend_df))], 'latency_ms': [14 + (i % 8) * 1.5 for i in range(len(trend_df))]})
    r3c3.line_chart(ai_df, x='date', y=['api_cost_estimate', 'latency_ms'], use_container_width=True)
