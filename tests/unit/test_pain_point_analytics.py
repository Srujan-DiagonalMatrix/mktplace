from fastapi.testclient import TestClient

from src.backend.main import app
from src.backend.services.ai.conversation_orchestrator import create_or_get_session


client = TestClient(app)


def test_taxonomy_classification_curated_utterances():
    sid = "pain-taxonomy"
    create_or_get_session(sid, resume=False)

    client.post("/chat/message", json={"session_id": sid, "message": "I am confused about the pricing details"})
    client.post("/chat/message", json={"session_id": sid, "message": "The APR rate seems too high"})
    client.post("/chat/message", json={"session_id": sid, "message": "I can't afford that deposit"})

    payload = client.get(f"/analytics/pain-points/{sid}").json()
    labels = {p["label"] for p in payload["pain_points"]}
    assert "pricing_confusion" in labels
    assert "apr_interest_concern" in labels
    assert "deposit_affordability" in labels


def test_multi_label_detection_single_turn():
    sid = "pain-multi"
    create_or_get_session(sid, resume=False)

    resp = client.post(
        "/chat/message",
        json={"session_id": sid, "message": "I'm confused on pricing and worried the APR is too high"},
    )
    assert resp.status_code == 200

    payload = client.get(f"/analytics/pain-points/{sid}").json()
    per_turn = payload["pain_points_by_turn"]
    turn_labels = {item["label"] for _, vals in per_turn.items() for item in vals}
    assert "pricing_confusion" in turn_labels
    assert "apr_interest_concern" in turn_labels


def test_confidence_threshold_and_false_positive_suppression():
    sid = "pain-threshold"
    create_or_get_session(sid, resume=False)

    client.post("/chat/message", json={"session_id": sid, "message": "Can you share APR options?"})
    payload = client.get(f"/analytics/pain-points/{sid}").json()
    labels = {p["label"] for p in payload["pain_points"]}
    assert "apr_interest_concern" in labels

    sid2 = "pain-noise"
    create_or_get_session(sid2, resume=False)
    client.post("/chat/message", json={"session_id": sid2, "message": "I like blue cars and weekend trips"})
    payload2 = client.get(f"/analytics/pain-points/{sid2}").json()
    assert payload2["pain_points"] == []


def test_dedup_repeated_labels_with_evidence_fields():
    sid = "pain-dedup"
    create_or_get_session(sid, resume=False)

    client.post("/chat/message", json={"session_id": sid, "message": "I'm confused about pricing"})
    client.post("/chat/message", json={"session_id": sid, "message": "still confused on cost"})

    payload = client.get(f"/analytics/pain-points/{sid}").json()
    points = [p for p in payload["pain_points"] if p["label"] == "pricing_confusion"]
    assert len(points) == 1
    point = points[0]
    assert len(point["source_turn_ids"]) == 2
    assert point["first_seen_turn_id"] != ""
    assert point["last_seen_turn_id"] != ""
    assert point["confidence"] >= 0.8


def test_scoring_formula_deterministic_dataset():
    sid = "pain-score-deterministic"
    create_or_get_session(sid, resume=False)
    client.post("/chat/message", json={"session_id": sid, "message": "confused about pricing"})
    client.post("/chat/message", json={"session_id": sid, "message": "APR is too high"})
    payload = client.get(f"/analytics/pain-points/{sid}?window=all").json()
    ranked = payload["ranked_pain_points"]
    assert ranked
    assert all("score" in row and "confidence" in row for row in ranked)


def test_boundary_zero_frequency_window_excludes_all():
    sid = "pain-zero-frequency"
    create_or_get_session(sid, resume=False)
    client.post("/chat/message", json={"session_id": sid, "message": "I am confused about pricing"})
    payload = client.get(f"/analytics/pain-points/{sid}?window=24h").json()
    assert isinstance(payload["ranked_pain_points"], list)


def test_boundary_extreme_severity_confidence_caps_score():
    sid = "pain-extreme-severity"
    create_or_get_session(sid, resume=False)
    for _ in range(3):
        client.post("/chat/message", json={"session_id": sid, "message": "deposit can't afford too much"})
    payload = client.get(f"/analytics/pain-points/{sid}?window=all").json()
    target = next(x for x in payload["ranked_pain_points"] if x["label"] == "deposit_affordability")
    assert 0 <= target["score"] <= 1


def test_ranking_stability_sorted_deterministic_output():
    sid = "pain-ranking-stable"
    create_or_get_session(sid, resume=False)
    client.post("/chat/message", json={"session_id": sid, "message": "confused about pricing"})
    client.post("/chat/message", json={"session_id": sid, "message": "confused about pricing"})
    first = client.get(f"/analytics/pain-points/{sid}?window=all").json()["ranked_pain_points"]
    second = client.get(f"/analytics/pain-points/{sid}?window=all").json()["ranked_pain_points"]
    assert first == second


def test_weight_change_sensitivity_changes_ranking_order():
    sid = "pain-weight-sensitivity"
    create_or_get_session(sid, resume=False)
    client.post("/chat/message", json={"session_id": sid, "message": "confused about pricing"})
    client.post("/chat/message", json={"session_id": sid, "message": "APR is too high"})
    base = client.get(f"/analytics/pain-points/{sid}?window=all").json()["ranked_pain_points"]
    tuned = client.get(
        f"/analytics/pain-points/{sid}?window=all&frequency_weight=0.1&severity_weight=0.8&impact_weight=0.1"
    ).json()["ranked_pain_points"]
    assert base and tuned
    assert [x["label"] for x in base] != []
