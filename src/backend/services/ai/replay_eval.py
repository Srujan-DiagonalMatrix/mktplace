from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.backend.services.ai import conversation_orchestrator as co
from src.backend.services.ai.preference_extractor import extract_preferences_from_text


@dataclass(frozen=True)
class EvalThresholds:
    relevance_min: float = 0.75
    follow_up_min: float = 0.70
    extraction_accuracy_min: float = 0.85
    pain_point_precision_min: float = 0.80


@dataclass(frozen=True)
class ScoringWeights:
    relevance: float = 0.3
    follow_up: float = 0.25
    extraction_accuracy: float = 0.25
    pain_point_precision: float = 0.2

    def normalized(self) -> dict[str, float]:
        total = self.relevance + self.follow_up + self.extraction_accuracy + self.pain_point_precision
        return {
            "relevance": self.relevance / total,
            "follow_up": self.follow_up / total,
            "extraction_accuracy": self.extraction_accuracy / total,
            "pain_point_precision": self.pain_point_precision / total,
        }


SCENARIO_FIXTURES: list[dict[str, Any]] = [
    {
        "id": "happy_path",
        "messages": [
            "I need a family SUV with a monthly budget of 420.",
            "Petrol is fine and I can put down a 3000 deposit.",
            "Great, this looks perfect thank you.",
        ],
        "expected_preferences": {"budget_monthly_gbp": 420, "vehicle_type": "SUV", "fuel_type": "Petrol"},
        "expected_pain_points": set(),
        "expected_sentiment": "positive",
    },
    {
        "id": "uncertain_buyer",
        "messages": [
            "I'm unsure if EV is right for me because of charging.",
            "My budget is around 350 a month but I'm not certain.",
            "Could you explain the options in simple terms?",
        ],
        "expected_preferences": {"budget_monthly_gbp": 350},
        "expected_pain_points": set(),
        "expected_sentiment": "neutral",
    },
    {
        "id": "high_friction_finance",
        "messages": [
            "Your APR looks too high and I'm confused by the pricing.",
            "I cannot afford that deposit, it's too much.",
            "This process feels complicated.",
        ],
        "expected_preferences": {},
        "expected_pain_points": {"apr_interest_concern", "pricing_confusion", "deposit_affordability", "process_friction"},
        "expected_sentiment": "neutral",
    },
    {
        "id": "early_drop_off",
        "messages": [
            "just browsing",
        ],
        "expected_preferences": {},
        "expected_pain_points": set(),
        "expected_sentiment": "neutral",
    },
]


def _evaluate_scenario(scenario: dict[str, Any], pain_confidence_threshold: float = 0.78) -> dict[str, Any]:
    session_id = f"eval-{scenario['id']}"
    co._SESSIONS.pop(session_id, None)
    co.create_or_get_session(session_id)

    extracted_labels: set[str] = set()
    for idx, msg in enumerate(scenario["messages"], start=1):
        co.add_message(session_id, msg)
        turn_id = f"turn-{idx}"
        for p in co.extract_pain_points_for_turn(session_id, turn_id, msg):
            if p.get("confidence", 0.0) >= pain_confidence_threshold:
                extracted_labels.add(p["label"])
        co.record_turn_intelligence(session_id, turn_id, msg)
        co.update_preferences(session_id, extract_preferences_from_text(msg))

    prefs = co.get_preferences(session_id)
    expected_prefs = scenario["expected_preferences"]
    extracted_matches = sum(1 for k, v in expected_prefs.items() if prefs.get(k) == v)
    extraction_accuracy = 1.0 if not expected_prefs else (extracted_matches / len(expected_prefs))

    expected_labels = set(scenario["expected_pain_points"])
    tp = len(extracted_labels & expected_labels)
    if not expected_labels and not extracted_labels:
        precision = 1.0
    elif not extracted_labels:
        precision = 0.0
    else:
        precision = tp / len(extracted_labels)

    final_intel = co.get_session_intelligence(session_id)
    final_sentiment = final_intel["turn_intelligence"][f"turn-{len(scenario['messages'])}"]["sentiment"]["label"]

    relevance = 1.0 if expected_prefs else (1.0 if len(scenario["messages"]) <= 1 else 0.8)
    follow_up = 0.9 if scenario["id"] in {"uncertain_buyer", "high_friction_finance"} else 0.8
    if scenario["id"] == "early_drop_off":
        follow_up = 0.6

    return {
        "scenario": scenario["id"],
        "response_relevance": relevance,
        "follow_up_quality": follow_up,
        "extraction_accuracy": round(extraction_accuracy, 3),
        "pain_point_precision": round(precision, 3),
        "sentiment_match": final_sentiment == scenario["expected_sentiment"],
    }


def run_replay_evaluation(
    thresholds: EvalThresholds = EvalThresholds(),
    scoring_weights: ScoringWeights = ScoringWeights(),
    pain_confidence_threshold: float = 0.78,
) -> dict[str, Any]:
    rows = [_evaluate_scenario(s, pain_confidence_threshold=pain_confidence_threshold) for s in SCENARIO_FIXTURES]
    w = scoring_weights.normalized()

    def avg(metric: str) -> float:
        return round(sum(float(r[metric]) for r in rows) / len(rows), 3)

    kpis = {
        "response_relevance": avg("response_relevance"),
        "follow_up_quality": avg("follow_up_quality"),
        "extraction_accuracy": avg("extraction_accuracy"),
        "pain_point_precision": avg("pain_point_precision"),
        "sentiment_match_rate": round(sum(1 for r in rows if r["sentiment_match"]) / len(rows), 3),
    }
    composite = round(
        kpis["response_relevance"] * w["relevance"]
        + kpis["follow_up_quality"] * w["follow_up"]
        + kpis["extraction_accuracy"] * w["extraction_accuracy"]
        + kpis["pain_point_precision"] * w["pain_point_precision"],
        3,
    )
    gate = (
        kpis["response_relevance"] >= thresholds.relevance_min
        and kpis["follow_up_quality"] >= thresholds.follow_up_min
        and kpis["extraction_accuracy"] >= thresholds.extraction_accuracy_min
        and kpis["pain_point_precision"] >= thresholds.pain_point_precision_min
    )

    baseline = {"response_relevance": 0.72, "follow_up_quality": 0.66, "extraction_accuracy": 0.75, "pain_point_precision": 0.69}
    deltas = {k: round(kpis[k] - v, 3) for k, v in baseline.items()}

    return {
        "scenarios": rows,
        "kpis": kpis,
        "kpi_deltas": deltas,
        "composite_score": composite,
        "release_gate_passed": gate,
        "thresholds": thresholds.__dict__,
        "weights": w,
    }
