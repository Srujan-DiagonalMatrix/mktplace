from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.ai.conversation_orchestrator import create_or_get_session

client = TestClient(app)


def _seed():
    sid = 'analytics-seed'
    create_or_get_session(sid, resume=False)
    client.post('/chat/message', json={'session_id': sid, 'message': "I'm worried APR is too high"})
    client.post('/chat/message', json={'session_id': sid, 'message': 'Can you explain pricing?'})


def test_dashboard_schema_and_keys():
    _seed()
    payload = client.get('/analytics/dashboard').json()
    assert {'filters', 'kpis', 'top_pain_points', 'sentiment_trends', 'dropoff_funnel', 'recurring_objections', 'recurring_faqs', 'session_drilldown', 'recommended_actions'} <= set(payload)


def test_dashboard_filter_stage_correctness():
    _seed()
    payload = client.get('/analytics/dashboard?stage=decision').json()
    assert payload['filters']['stage'] == 'decision'
