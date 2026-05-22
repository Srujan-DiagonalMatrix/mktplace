from src.frontend.components.analytics_dashboard import (
    _build_interaction_rows,
    _infer_icp_mix,
    _normalize_top_pain_points,
)


def test_normalize_top_pain_points_limits_to_five():
    payload = {"top_pain_points": [{"label": f"x{i}", "frequency": i, "max_confidence": 0.5} for i in range(10)]}
    rows = _normalize_top_pain_points(payload)
    assert len(rows) == 5
    assert rows[0]["rank"] == 1


def test_infer_icp_mix_returns_counts():
    payload = {"session_drilldown": [{"turns": 12, "pain_points": ["family_size"]}, {"turns": 3, "pain_points": []}]}
    mix = _infer_icp_mix(payload)
    labels = {m["profile"] for m in mix}
    assert "Family" in labels
    assert "Student" in labels


def test_build_interaction_rows_shape():
    payload = {"session_drilldown": [{"session_id": "abc", "turns": 4, "pain_points": ["budget"], "sentiment": 0.2}]}
    rows = _build_interaction_rows(payload)
    assert rows[0]["interaction_id"] == "abc"
    assert rows[0]["duration_min"] == 8
