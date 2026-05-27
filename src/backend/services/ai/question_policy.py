from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QuestionSpec:
    key: str
    question: str
    purpose: str
    category: str
    required: bool = False


@dataclass(frozen=True)
class PolicyDecision:
    assistant_action: str
    target_slot: str | None
    reason: str
    confidence: float
    fallback_action: str
    question_spec: QuestionSpec | None


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
    decision = decide_next_action(preferences, asked_keys, user_message, hesitation_count)
    return decision.question_spec


def decide_next_action(preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int) -> PolicyDecision:
    intent = str(preferences.get("intent") or "default").lower()
    bank = QUESTION_BANK_BY_INTENT.get(intent, QUESTION_BANK_BY_INTENT["default"])
    normalized = (user_message or "").strip().lower()
    ambiguous = normalized in {"maybe", "not sure", "idk", "unsure", "depends"}
    conflict = " but " in normalized and ("petrol" in normalized and "diesel" in normalized)
    if ambiguous or conflict:
        return PolicyDecision(
            assistant_action="clarify_with_options",
            target_slot="clarification",
            reason="user response was ambiguous or conflicting",
            confidence=0.95,
            fallback_action="ask_follow_up",
            question_spec=CLARIFICATION_QUESTION,
        )
    if hesitation_count >= 2:
        missing_critical = [q for q in bank if q.required and preferences.get(q.key) in (None, "")]
        if missing_critical:
            q = missing_critical[0]
            return PolicyDecision(
                assistant_action="ask_follow_up",
                target_slot=q.key,
                reason="repeat hesitation, prioritize critical missing field",
                confidence=0.85,
                fallback_action="clarify_with_options",
                question_spec=q,
            )
    for q in bank:
        if not q.required:
            continue
        if preferences.get(q.key) in (None, "") and q.key not in asked_keys:
            return PolicyDecision(
                assistant_action="ask_follow_up",
                target_slot=q.key,
                reason="next unresolved field not yet asked",
                confidence=0.9,
                fallback_action="clarify_with_options",
                question_spec=q,
            )
    for q in bank:
        if not q.required:
            continue
        if preferences.get(q.key) in (None, ""):
            return PolicyDecision(
                assistant_action="ask_follow_up",
                target_slot=q.key,
                reason="remaining unresolved field",
                confidence=0.75,
                fallback_action="clarify_with_options",
                question_spec=q,
            )
    return PolicyDecision(
        assistant_action="summarize_and_recommend",
        target_slot=None,
        reason="required fields captured",
        confidence=0.9,
        fallback_action="ask_follow_up",
        question_spec=None,
    )
