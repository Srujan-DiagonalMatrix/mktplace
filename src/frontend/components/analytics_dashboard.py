from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st




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

def render_analytics_dashboard(client: Any) -> None:
    st.markdown(
        """
        <div style="padding: 0.35rem 0 0.9rem 0;">
          <h1 style="margin:0; font-size:2rem; font-weight:800; letter-spacing:-0.02em;">Customer Insights</h1>
          <p style="margin:0.35rem 0 0; color:#6b7280; font-size:0.98rem;">Executive analytics for customer conversations, funnel health, and outcomes.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    start = date.today() - timedelta(days=29)
    end = date.today()

    payload = _load_dashboard_payload(client, start, end)

    _kpi_cards(_build_demo_dataframe(payload))

    trend_df = _build_demo_dataframe(payload)

    _render_section('Conversation & Conversion')
    r1c1, r1c2 = st.columns(2)
    r1c1.line_chart(trend_df, x='date', y=['sessions', 'enquiries', 'conversions'], use_container_width=True)
    r1c2.area_chart(trend_df, x='date', y=['dropoffs'], use_container_width=True)

    r2c1, r2c2 = st.columns(2)
    funnel = pd.DataFrame(
        {
            'stage': ['Conversation started', 'Enquiry submitted', 'Shortlisted', 'Converted'],
            'count': [
                int(trend_df['sessions'].sum()),
                int(trend_df['enquiries'].sum()),
                int(trend_df['enquiries'].sum() * 0.45),
                int(trend_df['conversions'].sum()),
            ],
        }
    ).set_index('stage')
    r2c1.bar_chart(funnel, horizontal=True, use_container_width=True)
    channel_df = pd.DataFrame(
        {
            'channel': ['Web', 'Chat', 'WhatsApp', 'Phone'],
            'Enquiry rate': [36, 40, 31, 24],
            'Conversion rate': [11, 13, 9, 7],
            'Drop-off rate': [17, 14, 19, 22],
        }
    ).set_index('channel')
    r2c2.bar_chart(channel_df, use_container_width=True)

    _render_section('Sentiment, Intent & Themes')
    r3c1, r3c2, r3c3 = st.columns(3)
    sentiment = pd.DataFrame({'sentiment': ['Positive', 'Neutral', 'Negative'], 'count': [52, 34, 14]}).set_index('sentiment')
    r3c1.bar_chart(sentiment, use_container_width=True)
    r3c2.line_chart(trend_df, x='date', y=['sentiment_score', 'intent_score'], use_container_width=True)
    themes = pd.DataFrame(
        {
            'theme': ['Pricing', 'Availability', 'Finance', 'Trade-in', 'Features'],
            'frequency': [112, 96, 88, 61, 59],
        }
    ).set_index('theme')
    r3c3.bar_chart(themes, horizontal=True, use_container_width=True)

    _render_section('Vehicle, Finance & AI Operations')
    r4c1, r4c2, r4c3 = st.columns(3)
    top_cars = pd.DataFrame(
        {
            'car': ['Tesla Model Y', 'Kia EV6', 'Hyundai Tucson', 'Toyota RAV4', 'BMW iX1'],
            'views': [182, 165, 154, 139, 128],
            'shortlists': [61, 55, 47, 43, 39],
        }
    ).set_index('car')
    r4c1.bar_chart(top_cars[['views', 'shortlists']], horizontal=True, use_container_width=True)

    finance = pd.DataFrame(
        {
            'category': ['Ready', 'Need Advice', 'Not Ready'],
            'count': [44, 38, 18],
        }
    ).set_index('category')
    r4c2.bar_chart(finance, use_container_width=True)

    ai_df = pd.DataFrame(
        {
            'date': trend_df['date'],
            'api_cost_estimate': [22 + i * 0.6 for i in range(len(trend_df))],
            'latency_ms': [620 + (i % 8) * 14 for i in range(len(trend_df))],
        }
    )
    r4c3.line_chart(ai_df, x='date', y=['api_cost_estimate', 'latency_ms'], use_container_width=True)

