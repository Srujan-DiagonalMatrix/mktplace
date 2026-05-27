from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class QuestionSpec:
    key: str
    question: str
    purpose: str
    category: str
    required: bool = False


QUESTION_BANK_BY_INTENT: dict[str, list[QuestionSpec]] = {
    "purchase": [
        QuestionSpec("fuel_type", "What type of fuel would you prefer for your next vehicle?", "collect_powertrain_preference", "critical", True),
        QuestionSpec("monthly_from_gbp", "What monthly budget would you like to stay within?", "collect_budget_limit", "critical", True),
        QuestionSpec("transmission", "Do you have a preferred transmission type?", "collect_driving_preference", "required", True),
        QuestionSpec("doors", "How many doors would you prefer?", "collect_practical_layout", "optional", False),
        QuestionSpec("seats", "How many seats do you need?", "collect_capacity_needs", "optional", False),
        QuestionSpec("term_months", "What finance term would suit you best?", "collect_finance_term", "required", True),
    ],
    "default": [
        QuestionSpec("fuel_type", "What type of fuel would you prefer for your next vehicle?", "collect_powertrain_preference", "critical", True),
        QuestionSpec("transmission", "Do you have a preferred transmission type?", "collect_driving_preference", "required", True),
        QuestionSpec("monthly_from_gbp", "What monthly budget would you like to stay within?", "collect_budget_limit", "required", True),
        QuestionSpec("doors", "How many doors would you prefer?", "collect_practical_layout", "optional", False),
        QuestionSpec("seats", "How many seats do you need?", "collect_capacity_needs", "optional", False),
    ],
}

CLARIFICATION_QUESTION = QuestionSpec(
    key="clarification",
    question="I want to make sure I understood correctly — could you clarify your preference?",
    purpose="resolve_answer_ambiguity",
    category="clarification",
    required=True,
)


Stage = Literal["discover", "narrow", "clarify", "summarize", "recommend"]


@dataclass(frozen=True)
class PolicyDecision:
    stage: Stage
    action: str
    question: QuestionSpec | None = None


def _missing_slots(bank: list[QuestionSpec], preferences: dict) -> list[QuestionSpec]:
    return [q for q in bank if preferences.get(q.key) in (None, "")]


def _required_slots(bank: list[QuestionSpec]) -> list[QuestionSpec]:
    return [q for q in bank if q.required]


def _is_answer_ambiguous(user_message: str, hesitation_count: int) -> bool:
    normalized = (user_message or "").strip().lower()
    ambiguous_tokens = {"maybe", "not sure", "idk", "unsure", "depends"}
    return normalized in ambiguous_tokens or hesitation_count >= 3


def _has_contradiction(preferences: dict, user_message: str) -> bool:
    normalized = (user_message or "").strip().lower()
    conflict_markers = preferences.get("contradiction_markers") or []
    has_marker_conflict = bool(conflict_markers)
    message_conflict = " but " in normalized and ("petrol" in normalized and "diesel" in normalized)
    return has_marker_conflict or message_conflict


def _sufficiency_reached(bank: list[QuestionSpec], preferences: dict) -> bool:
    required_ready = all(preferences.get(q.key) not in (None, "") for q in _required_slots(bank))
    themes = preferences.get("extracted_themes") or []
    sentiment = str(preferences.get("sentiment") or "").strip().lower()
    has_signal_depth = len(themes) >= 1 or sentiment in {"positive", "neutral", "negative"}
    return required_ready and has_signal_depth


def select_policy_decision(preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int) -> PolicyDecision:
    intent = str(preferences.get("intent") or "default").lower()
    bank = QUESTION_BANK_BY_INTENT.get(intent, QUESTION_BANK_BY_INTENT["default"])
    missing = _missing_slots(bank, preferences)

    if _has_contradiction(preferences, user_message):
        return PolicyDecision(stage="clarify", action="resolve_contradiction", question=CLARIFICATION_QUESTION)

    if _is_answer_ambiguous(user_message, hesitation_count):
        if hesitation_count >= 2 and missing:
            # Ambiguity loop recovery: move from endless clarification back to concrete collection.
            return PolicyDecision(stage="narrow", action="recover_from_ambiguity", question=missing[0])
        return PolicyDecision(stage="clarify", action="resolve_ambiguity", question=CLARIFICATION_QUESTION)

    if _sufficiency_reached(bank, preferences):
        if preferences.get("summary_presented"):
            return PolicyDecision(stage="recommend", action="present_recommendations")
        return PolicyDecision(stage="summarize", action="summarize_preferences")

    missing_required = [q for q in _required_slots(bank) if preferences.get(q.key) in (None, "")]
    for q in missing_required:
        if q.key not in asked_keys:
            return PolicyDecision(stage="discover", action="collect_required_slot", question=q)
    if missing_required:
        return PolicyDecision(stage="discover", action="revisit_required_slot", question=missing_required[0])

    for q in bank:
        if preferences.get(q.key) in (None, "") and q.key not in asked_keys:
            return PolicyDecision(stage="narrow", action="collect_optional_slot", question=q)
    for q in bank:
        if preferences.get(q.key) in (None, ""):
            return PolicyDecision(stage="narrow", action="revisit_optional_slot", question=q)
    return PolicyDecision(stage="recommend", action="present_recommendations")


def select_next_question(preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int) -> QuestionSpec | None:
    return select_policy_decision(preferences, asked_keys, user_message, hesitation_count).question
