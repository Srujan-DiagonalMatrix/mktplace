from src.frontend.components.analytics_dashboard import transform_sentiment_trends


def test_transform_sentiment_payload_to_chart_rows():
    rows = transform_sentiment_trends({'sentiment_trends': {'2026-05-20': {'positive': 1, 'neutral': 2, 'negative': 3}}})
    assert rows == [{'date': '2026-05-20', 'positive': 1, 'neutral': 2, 'negative': 3}]


def test_transform_empty_state():
    assert transform_sentiment_trends({'sentiment_trends': {}}) == []


def test_load_dashboard_payload_fallback_when_backend_unavailable(monkeypatch):
    from src.frontend.components import analytics_dashboard as dashboard

    notices: list[str] = []
    monkeypatch.setattr(dashboard.st, "warning", lambda msg: notices.append(msg))

    class BrokenClient:
        def get_analytics_dashboard(self, **_kwargs):
            raise ConnectionError("backend down")

    payload = dashboard._load_dashboard_payload(BrokenClient(), dashboard.date(2026, 4, 23), dashboard.date(2026, 5, 22))

    assert payload == {}
    assert notices == ['Analytics backend is unavailable. Showing demo insights.']
