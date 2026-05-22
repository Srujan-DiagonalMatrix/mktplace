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
