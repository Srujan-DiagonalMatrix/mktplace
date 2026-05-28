from __future__ import annotations

from src.backend.services.ai.conversation_orchestrator import (
    create_or_get_session,
    get_context_preferences,
    get_next_question_variant_index,
    get_memory,
    get_memory_snapshots,
    get_preferences,
    set_last_question_delay_seconds,
    update_preferences,
)


def test_merge_conflict_resolution_prefers_high_confidence_new_value():
    sid = "mem-merge-1"
    create_or_get_session(sid, resume=False)
    update_preferences(sid, {"fuel_type": "EV"})
    update_preferences(sid, {"fuel_type": "Electric"})

    prefs = get_preferences(sid)
    memory = get_memory(sid)

    assert prefs["fuel_type"] == "Electric"
    assert memory["fuel_type"]["confidence"] >= 0.75


def test_snapshot_consistency_across_turns():
    sid = "mem-snap-1"
    create_or_get_session(sid, resume=False)
    update_preferences(sid, {"monthly_budget": 400})
    update_preferences(sid, {"term_months": 48})

    snapshots = get_memory_snapshots(sid)
    assert len(snapshots) == 2
    assert snapshots[0]["preferences"]["monthly_budget"] == 400
    assert snapshots[1]["preferences"]["term_months"] == 48


def test_resume_reloads_existing_session_state():
    sid = "mem-resume-1"
    create_or_get_session(sid, resume=False)
    update_preferences(sid, {"fuel_type": "Diesel", "deposit_gbp": 2000})

    resumed = create_or_get_session(sid, resume=True)
    assert resumed["session_id"] == sid
    assert get_preferences(sid)["fuel_type"] == "Diesel"


def test_confidence_threshold_blocks_low_confidence_updates():
    sid = "mem-conf-1"
    create_or_get_session(sid, resume=False)
    update_preferences(sid, {"fuel_type": "diesel"}, min_confidence=0.5)
    update_preferences(sid, {"fuel_type": "x"}, min_confidence=0.5)

    prefs = get_preferences(sid)
    assert prefs["fuel_type"] == "diesel"


def test_retrieval_latest_and_relevant_history_only():
    sid = "mem-context-1"
    create_or_get_session(sid, resume=False)
    update_preferences(sid, {"fuel_type": "Petrol", "term_months": 36, "monthly_budget": 500})

    filtered = get_context_preferences(sid, relevant_keys=["fuel_type", "monthly_from_gbp"])
    assert filtered == {"fuel_type": "Petrol", "budget_monthly_gbp": 500}


def test_question_variant_indices_cycle_in_session_state():
    sid = "mem-question-variants-1"
    session = create_or_get_session(sid, resume=False)

    assert get_next_question_variant_index(sid, "fuel_type", 3) == 0
    assert get_next_question_variant_index(sid, "fuel_type", 3) == 1
    assert get_next_question_variant_index(sid, "fuel_type", 3) == 2
    assert get_next_question_variant_index(sid, "fuel_type", 3) == 0
    assert session["question_variant_index_by_key"] == {"fuel_type": 1}


def test_last_question_delay_seconds_is_recorded_on_session():
    sid = "mem-question-delay-1"
    session = create_or_get_session(sid, resume=False)

    set_last_question_delay_seconds(sid, 2.75)

    assert session["last_question_delay_seconds"] == 2.75
