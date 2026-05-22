from src.frontend.components.analytics_dashboard import transform_sentiment_trends


def test_transform_sentiment_payload_to_chart_rows():
    rows = transform_sentiment_trends({'sentiment_trends': {'2026-05-20': {'positive': 1, 'neutral': 2, 'negative': 3}}})
    assert rows == [{'date': '2026-05-20', 'positive': 1, 'neutral': 2, 'negative': 3}]


def test_transform_empty_state():
    assert transform_sentiment_trends({'sentiment_trends': {}}) == []
