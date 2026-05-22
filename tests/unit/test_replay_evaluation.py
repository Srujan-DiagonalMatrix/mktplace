from src.backend.services.ai.replay_eval import (
    EvalThresholds,
    ScoringWeights,
    run_replay_evaluation,
)


def test_regression_suite_runs_all_required_scenarios():
    payload = run_replay_evaluation()
    ids = {row["scenario"] for row in payload["scenarios"]}
    assert {"happy_path", "uncertain_buyer", "high_friction_finance", "early_drop_off"} <= ids


def test_extraction_accuracy_matches_expected_structured_outputs():
    payload = run_replay_evaluation()
    assert payload["kpis"]["extraction_accuracy"] >= 0.85


def test_pain_point_sentiment_stability_across_tuning_versions():
    base = run_replay_evaluation(
        thresholds=EvalThresholds(),
        scoring_weights=ScoringWeights(),
        pain_confidence_threshold=0.78,
    )
    tuned = run_replay_evaluation(
        thresholds=EvalThresholds(),
        scoring_weights=ScoringWeights(relevance=0.28, follow_up=0.27, extraction_accuracy=0.25, pain_point_precision=0.2),
        pain_confidence_threshold=0.75,
    )
    assert base["kpis"]["sentiment_match_rate"] == tuned["kpis"]["sentiment_match_rate"]
    assert tuned["kpis"]["pain_point_precision"] >= base["kpis"]["pain_point_precision"] - 0.05


def test_release_gate_thresholds_must_pass():
    payload = run_replay_evaluation(
        thresholds=EvalThresholds(
            relevance_min=0.74,
            follow_up_min=0.68,
            extraction_accuracy_min=0.84,
            pain_point_precision_min=0.78,
        )
    )
    assert payload["release_gate_passed"] is True
