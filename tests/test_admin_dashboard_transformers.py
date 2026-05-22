from src.frontend.components.analytics_dashboard import (
    _build_conversation_history_rows,
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


def test_build_conversation_history_rows_has_required_columns_and_view():
    payload = {
        "session_drilldown": [
            {
                "session_id": "abc",
                "turns": 6,
                "pain_points": ["budget", "financing", "availability"],
                "sentiment": -0.4,
                "summary": "Customer is interested but blocked on financing.",
            }
        ]
    }
    rows = _build_conversation_history_rows(payload)
    required_columns = {
        "interaction_id",
        "date_of_interaction",
        "time_of_interaction",
        "customer_name",
        "contact_details",
        "channel",
        "summary_of_interaction",
        "top_5_pain_points",
        "weights",
        "seriousness_to_proceed",
        "icp_primary",
        "conversation_duration_min",
        "assigned_manager",
        "status",
        "view",
    }
    assert required_columns.issubset(rows[0].keys())
    assert rows[0]["view"] == "View"
    assert rows[0]["seriousness_to_proceed"] == "High"
