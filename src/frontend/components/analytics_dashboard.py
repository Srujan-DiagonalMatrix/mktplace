from __future__ import annotations

from typing import Any
import streamlit as st


def transform_sentiment_trends(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for day, sentiments in payload.get('sentiment_trends', {}).items():
        rows.append({'date': day, **sentiments})
    return rows


def render_analytics_dashboard(client: Any) -> None:
    st.subheader('Customer Friction Analytics')
    c1, c2, c3 = st.columns(3)
    start = c1.date_input('Start date', value=None)
    end = c2.date_input('End date', value=None)
    stage = c3.selectbox('Session stage', ['all', 'awareness', 'consideration', 'decision'])
    vc1, vc2 = st.columns(2)
    vehicle_type = vc1.text_input('Vehicle type filter')
    fuel_type = vc2.text_input('Fuel type filter')

    payload = client.get_analytics_dashboard(
        start_date=str(start) if start else None,
        end_date=str(end) if end else None,
        vehicle_type=vehicle_type or None,
        fuel_type=fuel_type or None,
        stage=None if stage == 'all' else stage,
    )
    k1, k2, k3, k4 = st.columns(4)
    kpis = payload.get('kpis', {})
    k1.metric('Sessions', kpis.get('sessions', 0))
    k2.metric('Negative days', kpis.get('top_negative_sentiment_days', 0))
    k3.metric('Drop-off', kpis.get('dropoff_total', 0))
    k4.metric('Pain points', kpis.get('unique_pain_points', 0))

    trend_rows = transform_sentiment_trends(payload)
    if trend_rows:
        st.line_chart(trend_rows, x='date', y=['positive', 'neutral', 'negative'])
    else:
        st.info('No trend data for current filters.')

    st.write('### Ranked pain points')
    if payload.get('top_pain_points'):
        st.dataframe(payload['top_pain_points'], use_container_width=True)
    else:
        st.info('No pain points found for selected filters.')

    st.write('### Session drill-down summary')
    drill = payload.get('session_drilldown', [])
    if drill:
        st.dataframe(drill, use_container_width=True)
    else:
        st.info('No sessions matched filters.')

    st.write('### Recommended actions')
    actions = payload.get('recommended_actions', [])
    if actions:
        for a in actions:
            st.markdown(f"**P{a['priority']}** · {a['action']}")
    else:
        st.info('No recommended actions available.')
