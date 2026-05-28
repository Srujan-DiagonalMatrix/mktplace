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


def test_curated_policy_priors_match_slot_state(tmp_path):
    from src.backend.services.ai.curated_runtime_adapter import CuratedInteractionAdapter

    (tmp_path / "dialogue_policy_labels.jsonl").write_text(
        "\n".join([
            '{"state":{"missing_required_slots":["fuel_type","transmission","monthly_from_gbp"],"hesitation_count":0},"gold_action":"ask_follow_up","gold_target_slot":"fuel_type"}',
            '{"state":{"missing_required_slots":["fuel_type","transmission","monthly_from_gbp"],"hesitation_count":0},"gold_action":"ask_follow_up","gold_target_slot":"fuel_type"}',
            '{"state":{"missing_required_slots":["fuel_type","transmission","monthly_from_gbp"],"hesitation_count":0},"gold_action":"clarify_with_options","gold_target_slot":"fuel_type"}',
        ]) + "\n",
        encoding="utf-8",
    )
    adapter = CuratedInteractionAdapter(base_dir=tmp_path)
    priors = adapter.get_policy_priors(preferences={}, hesitation_count=0)
    assert priors
    assert priors[0].target_slot == "fuel_type"
    assert abs(sum(p.weight for p in priors) - 1.0) < 1e-9


def test_decide_next_action_returns_present_recommendations_after_summary():
    from src.backend.services.ai.question_policy import decide_next_action

    prefs = {
        "intent": "purchase",
        "fuel_type": "Petrol",
        "monthly_from_gbp": 300,
        "transmission": "Automatic",
        "summary_presented": True,
    }
    decision = decide_next_action(prefs, asked_keys=[], user_message="Yes, show recommendations", hesitation_count=0)

    assert decision.assistant_action == "present_recommendations"
    assert decision.question_spec is None
