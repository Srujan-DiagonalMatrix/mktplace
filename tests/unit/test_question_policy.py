from src.backend.services.ai.question_policy import select_next_question


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


def test_decide_next_action_returns_summary_when_complete():
    from src.backend.services.ai.question_policy import decide_next_action

    prefs = {
        "intent": "purchase",
        "fuel_type": "Petrol",
        "monthly_from_gbp": 300,
        "transmission": "Automatic",
        "term_months": 36,
    }
    decision = decide_next_action(prefs, asked_keys=[], user_message="thanks", hesitation_count=0)
    assert decision.assistant_action == "summarize_and_recommend"
    assert decision.question_spec is None
