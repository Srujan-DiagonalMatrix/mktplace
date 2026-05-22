from __future__ import annotations

from dataclasses import dataclass


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


def select_next_question(preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int) -> QuestionSpec | None:
    intent = str(preferences.get("intent") or "default").lower()
    bank = QUESTION_BANK_BY_INTENT.get(intent, QUESTION_BANK_BY_INTENT["default"])
    normalized = (user_message or "").strip().lower()
    ambiguous = normalized in {"maybe", "not sure", "idk", "unsure", "depends"}
    conflict = " but " in normalized and ("petrol" in normalized and "diesel" in normalized)
    if ambiguous or conflict:
        return CLARIFICATION_QUESTION
    if hesitation_count >= 2:
        missing_critical = [q for q in bank if q.required and preferences.get(q.key) in (None, "")]
        if missing_critical:
            return missing_critical[0]
    for q in bank:
        if preferences.get(q.key) in (None, "") and q.key not in asked_keys:
            return q
    for q in bank:
        if preferences.get(q.key) in (None, ""):
            return q
    return None
