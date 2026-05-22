from datetime import datetime, timedelta

from src.backend.services.ai import conversation_orchestrator as co


def test_per_turn_sentiment_classification_benchmark_fixtures():
    fixtures = [
        ("I love this deal, great options", "positive"),
        ("I am worried this is too expensive", "negative"),
        ("Can you share the specs", "neutral"),
    ]
    for text, expected in fixtures:
        result = co.classify_sentiment_for_turn(text)
        assert result["label"] == expected
        assert 0.0 <= result["confidence"] <= 1.0
        assert "explainability" in result


def test_session_level_aggregation_correctness():
    sid = "intel-session"
    co.create_or_get_session(sid, resume=False)
    turns = [
        ("turn-1", "great and perfect"),
        ("turn-2", "worried about budget"),
        ("turn-3", "just checking details"),
    ]
    for tid, text in turns:
        co.record_turn_intelligence(sid, turn_id=tid, text=text)
    intelligence = co.get_session_intelligence(sid)
    assert intelligence["sentiment_summary"]["positive"] == 1
    assert intelligence["sentiment_summary"]["negative"] == 1
    assert intelligence["sentiment_summary"]["neutral"] == 1
    assert intelligence["session_sentiment_score"] == 0.0


def test_theme_normalization_synonym_collapse():
    assert co.normalize_theme_label("cost_stress") == "budget_anxiety"
    assert co.normalize_theme_label("charging concern") == "ev_uncertainty"


def test_date_range_aggregation_for_trend_outputs():
    sid = "trend-session"
    s = co.create_or_get_session(sid, resume=False)
    co.record_turn_intelligence(sid, "turn-a", "great budget")
    co.record_turn_intelligence(sid, "turn-b", "worried about apr")
    today = datetime.utcnow().date().isoformat()
    # inject dated meta entries matching the turn ids
    s["messages_meta"] = [
        {"turn_id": "turn-a", "created_at": datetime.utcnow() - timedelta(days=1)},
        {"turn_id": "turn-b", "created_at": datetime.utcnow()},
    ]
    res = co.aggregate_intelligence_trends(start_date=today, end_date=today)
    assert today in res["by_date"]
    assert res["by_date"][today]["sentiment"]["negative"] >= 1
