from src.backend.services.ai.question_policy import select_next_question, select_policy_decision


def test_missing_critical_preference_selected_first():
    q = select_next_question({"intent": "purchase"}, asked_keys=[], user_message="hello", hesitation_count=0)
    assert q is not None
    assert q.key == "fuel_type"


def test_ambiguity_routes_to_clarification():
    q = select_next_question({"intent": "purchase"}, asked_keys=["fuel_type"], user_message="maybe", hesitation_count=1)
    assert q is not None
    assert q.key == "clarification"
    assert q.category == "clarification"


def test_conflict_routes_to_clarification():
    q = select_next_question({"intent": "purchase"}, asked_keys=[], user_message="petrol but diesel", hesitation_count=0)
    assert q is not None
    assert q.key == "clarification"


def test_anti_repetition_skips_already_asked_when_possible():
    q = select_next_question({"intent": "purchase"}, asked_keys=["fuel_type"], user_message="ok", hesitation_count=0)
    assert q is not None
    assert q.key != "fuel_type"


def test_repetition_allowed_when_needed_for_unfilled_slot():
    q = select_next_question({"intent": "purchase", "fuel_type": ""}, asked_keys=["fuel_type", "monthly_from_gbp", "transmission", "doors", "seats", "term_months"], user_message="ok", hesitation_count=0)
    assert q is not None
    assert q.key == "fuel_type"


def test_slot_completion_progression_to_next_slot():
    prefs = {"intent": "purchase", "fuel_type": "Petrol", "monthly_from_gbp": 400}
    q = select_next_question(prefs, asked_keys=["fuel_type", "monthly_from_gbp"], user_message="ok", hesitation_count=0)
    assert q is not None
    assert q.key == "transmission"


def test_hesitation_prioritizes_missing_critical():
    prefs = {"intent": "purchase", "fuel_type": "Diesel"}
    q = select_next_question(prefs, asked_keys=["fuel_type"], user_message="hmm", hesitation_count=2)
    assert q is not None
    assert q.key == "monthly_from_gbp"


def test_ambiguity_loop_recovery():
    prefs = {"intent": "purchase"}
    decision = select_policy_decision(prefs, asked_keys=["fuel_type"], user_message="maybe", hesitation_count=3)
    assert decision.stage == "narrow"
    assert decision.action == "recover_from_ambiguity"
    assert decision.question is not None
    assert decision.question.key == "fuel_type"


def test_non_repetition_after_answered_slots():
    prefs = {"intent": "purchase", "fuel_type": "Petrol"}
    decision = select_policy_decision(prefs, asked_keys=["fuel_type"], user_message="ok", hesitation_count=0)
    assert decision.question is not None
    assert decision.question.key != "fuel_type"


def test_contradiction_resolution_before_new_slot_collection():
    prefs = {"intent": "purchase", "contradiction_markers": ["fuel_type_conflict"]}
    decision = select_policy_decision(prefs, asked_keys=[], user_message="ok", hesitation_count=0)
    assert decision.stage == "clarify"
    assert decision.action == "resolve_contradiction"
    assert decision.question is not None
    assert decision.question.key == "clarification"


def test_summarize_then_recommend_transition_when_sufficiency_reached():
    prefs = {
        "intent": "purchase",
        "fuel_type": "Hybrid",
        "monthly_from_gbp": 450,
        "transmission": "Automatic",
        "term_months": 36,
        "extracted_themes": ["efficiency"],
        "sentiment": "positive",
    }
    summarize = select_policy_decision(prefs, asked_keys=["fuel_type", "monthly_from_gbp", "transmission", "term_months"], user_message="ok", hesitation_count=0)
    assert summarize.stage == "summarize"
    assert summarize.action == "summarize_preferences"
    assert summarize.question is None

    recommend = select_policy_decision({**prefs, "summary_presented": True}, asked_keys=["fuel_type", "monthly_from_gbp", "transmission", "term_months"], user_message="ok", hesitation_count=0)
    assert recommend.stage == "recommend"
    assert recommend.action == "present_recommendations"
    assert recommend.question is None
