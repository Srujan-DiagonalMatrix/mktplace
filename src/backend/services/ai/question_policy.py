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
    variants: tuple[str, ...] = ()


Stage = Literal["discover", "narrow", "clarify", "summarize", "recommend"]


@dataclass(frozen=True)
class PolicyDecision:
    # New-style policy fields
    stage: Stage | None = None
    action: str | None = None
    question: QuestionSpec | None = None
    # Legacy/API fields retained for compatibility
    assistant_action: str | None = None
    target_slot: str | None = None
    reason: str | None = None
    confidence: float | None = None
    fallback_action: str | None = None
    question_spec: QuestionSpec | None = None


QUESTION_BANK_BY_INTENT: dict[str, list[QuestionSpec]] = {
    "purchase": [
        QuestionSpec(
            "fuel_type",
            "What type of fuel would you prefer for your next vehicle?",
            "collect_powertrain_preference",
            "critical",
            True,
            (
                "Which fuel type would you like me to focus on for your next vehicle?",
                "Do you have a fuel preference for the vehicle you’re looking for?",
            ),
        ),
        QuestionSpec(
            "transmission",
            "Do you have a preferred transmission type?",
            "collect_driving_preference",
            "required",
            True,
            (
                "Would you prefer manual or automatic transmission?",
                "What transmission type should I prioritise for you?",
            ),
        ),
        QuestionSpec(
            "monthly_from_gbp",
            "What monthly budget would you like to stay within?",
            "collect_budget_limit",
            "critical",
            True,
            (
                "Roughly what monthly payment would feel comfortable for you?",
                "What monthly budget should I use when filtering options?",
            ),
        ),
        QuestionSpec(
            "doors",
            "How many doors would you prefer?",
            "collect_practical_layout",
            "optional",
            False,
            (
                "Would you like a specific number of doors?",
                "How many doors would work best for how you’ll use the car?",
            ),
        ),
        QuestionSpec(
            "seats",
            "How many seats do you need?",
            "collect_capacity_needs",
            "optional",
            False,
            (
                "How many people does the vehicle need to seat?",
                "What seating capacity should I look for?",
            ),
        ),
        QuestionSpec(
            "term_months",
            "What finance term would suit you best?",
            "collect_finance_term",
            "optional",
            False,
            (
                "How long would you like the finance agreement to run?",
                "Do you have a preferred finance term in months?",
            ),
        ),
    ],
    "default": [
        QuestionSpec(
            "fuel_type",
            "What type of fuel would you prefer for your next vehicle?",
            "collect_powertrain_preference",
            "critical",
            True,
            (
                "Which fuel type would you like me to focus on for your next vehicle?",
                "Do you have a fuel preference for the vehicle you’re looking for?",
            ),
        ),
        QuestionSpec(
            "transmission",
            "Do you have a preferred transmission type?",
            "collect_driving_preference",
            "required",
            True,
            (
                "Would you prefer manual or automatic transmission?",
                "What transmission type should I prioritise for you?",
            ),
        ),
        QuestionSpec(
            "monthly_from_gbp",
            "What monthly budget would you like to stay within?",
            "collect_budget_limit",
            "required",
            True,
            (
                "Roughly what monthly payment would feel comfortable for you?",
                "What monthly budget should I use when filtering options?",
            ),
        ),
        QuestionSpec(
            "doors",
            "How many doors would you prefer?",
            "collect_practical_layout",
            "optional",
            False,
            (
                "Would you like a specific number of doors?",
                "How many doors would work best for how you’ll use the car?",
            ),
        ),
        QuestionSpec(
            "seats",
            "How many seats do you need?",
            "collect_capacity_needs",
            "optional",
            False,
            (
                "How many people does the vehicle need to seat?",
                "What seating capacity should I look for?",
            ),
        ),
        QuestionSpec("fuel_type", "What type of fuel would you prefer for your next vehicle?", "collect_powertrain_preference", "critical", True),
        QuestionSpec("transmission", "Do you have a preferred transmission type?", "collect_driving_preference", "required", True),
        QuestionSpec("monthly_from_gbp", "What monthly budget would you like to stay within?", "collect_budget_limit", "critical", True),
        QuestionSpec("doors", "How many doors would you prefer?", "collect_practical_layout", "optional", False),
        QuestionSpec("seats", "How many seats do you need?", "collect_capacity_needs", "optional", False),
        QuestionSpec("term_months", "What finance term would suit you best?", "collect_finance_term", "optional", False),
        QuestionSpec("body_type", "What body type are you most interested in, such as SUV, hatchback, saloon, or estate?", "collect_vehicle_shape_preference", "vehicle_discovery", False),
        QuestionSpec("make_preference", "Do you have a preferred make or brand?", "collect_brand_preference", "vehicle_discovery", False),
        QuestionSpec("model_preference", "Is there a specific model you already have in mind?", "collect_model_preference", "vehicle_discovery", False),
        QuestionSpec("annual_mileage_limit", "Roughly how many miles do you expect to drive each year?", "collect_annual_mileage_for_finance", "finance", False),
        QuestionSpec("deposit_gbp", "How much deposit would you like to put down, if any?", "collect_deposit_amount", "finance", False),
        QuestionSpec("usage_type", "How will you mainly use the vehicle — commuting, family trips, business, or something else?", "collect_primary_usage", "lifestyle", False),
        QuestionSpec("must_have_features", "Are there any must-have features you want included?", "collect_feature_requirements", "vehicle_discovery", False),
        QuestionSpec("colour_preference", "Do you have a preferred colour or colours to avoid?", "collect_colour_preference", "vehicle_discovery", False),
        QuestionSpec("age_limit_years", "What is the oldest vehicle age you would consider?", "collect_vehicle_age_limit", "vehicle_discovery", False),
        QuestionSpec("delivery_timeline", "When would you ideally like to have the vehicle delivered?", "collect_delivery_timeline", "timeline", False),
    ],
    "default": [
        QuestionSpec("fuel_type", "What type of fuel would you prefer for your next vehicle?", "collect_powertrain_preference", "critical", True),
        QuestionSpec("transmission", "Do you have a preferred transmission type?", "collect_driving_preference", "required", True),
        QuestionSpec("monthly_from_gbp", "What monthly budget would you like to stay within?", "collect_budget_limit", "required", True),
        QuestionSpec("doors", "How many doors would you prefer?", "collect_practical_layout", "optional", False),
        QuestionSpec("seats", "How many seats do you need?", "collect_capacity_needs", "optional", False),
        QuestionSpec("body_type", "What body type are you most interested in, such as SUV, hatchback, saloon, or estate?", "collect_vehicle_shape_preference", "vehicle_discovery", False),
        QuestionSpec("make_preference", "Do you have a preferred make or brand?", "collect_brand_preference", "vehicle_discovery", False),
        QuestionSpec("model_preference", "Is there a specific model you already have in mind?", "collect_model_preference", "vehicle_discovery", False),
        QuestionSpec("annual_mileage_limit", "Roughly how many miles do you expect to drive each year?", "collect_annual_mileage_for_finance", "finance", False),
        QuestionSpec("deposit_gbp", "How much deposit would you like to put down, if any?", "collect_deposit_amount", "finance", False),
        QuestionSpec("usage_type", "How will you mainly use the vehicle — commuting, family trips, business, or something else?", "collect_primary_usage", "lifestyle", False),
        QuestionSpec("must_have_features", "Are there any must-have features you want included?", "collect_feature_requirements", "vehicle_discovery", False),
        QuestionSpec("colour_preference", "Do you have a preferred colour or colours to avoid?", "collect_colour_preference", "vehicle_discovery", False),
        QuestionSpec("age_limit_years", "What is the oldest vehicle age you would consider?", "collect_vehicle_age_limit", "vehicle_discovery", False),
        QuestionSpec("delivery_timeline", "When would you ideally like to have the vehicle delivered?", "collect_delivery_timeline", "timeline", False),
    ],
}


PURCHASE_DISCOVERY_QUESTIONS: tuple[QuestionSpec, ...] = (
    QuestionSpec("body_type", "What body type are you most interested in, such as SUV, hatchback, saloon, or estate?", "collect_vehicle_shape_preference", "vehicle_discovery", False),
    QuestionSpec("make_preference", "Do you have a preferred make or brand?", "collect_brand_preference", "vehicle_discovery", False),
    QuestionSpec("model_preference", "Is there a specific model you already have in mind?", "collect_model_preference", "vehicle_discovery", False),
    QuestionSpec("annual_mileage_limit", "Roughly how many miles do you expect to drive each year?", "collect_annual_mileage_for_finance", "finance", False),
    QuestionSpec("deposit_gbp", "How much deposit would you like to put down, if any?", "collect_deposit_amount", "finance", False),
    QuestionSpec("usage_type", "How will you mainly use the vehicle — commuting, family trips, business, or something else?", "collect_primary_usage", "lifestyle", False),
    QuestionSpec("must_have_features", "Are there any must-have features you want included?", "collect_feature_requirements", "vehicle_discovery", False),
    QuestionSpec("colour_preference", "Do you have a preferred colour or colours to avoid?", "collect_colour_preference", "vehicle_discovery", False),
    QuestionSpec("age_limit_years", "What is the oldest vehicle age you would consider?", "collect_vehicle_age_limit", "vehicle_discovery", False),
    QuestionSpec("delivery_timeline", "When would you ideally like to have the vehicle delivered?", "collect_delivery_timeline", "timeline", False),
)
QUESTION_BANK_BY_INTENT["purchase"].extend(PURCHASE_DISCOVERY_QUESTIONS)

CLARIFICATION_QUESTION = QuestionSpec(
    key="clarification",
    question="I want to make sure I understood correctly — could you clarify your preference?",
    purpose="resolve_answer_ambiguity",
    category="clarification",
    required=True,
    variants=(
        "Could you clarify that preference so I can match the right vehicles?",
        "I want to make sure I’m filtering correctly — can you say a little more?",
    ),
)


def get_question_spec_for_slot(slot: str, preferences: dict) -> QuestionSpec | None:
    if slot == CLARIFICATION_QUESTION.key:
        return CLARIFICATION_QUESTION

    intent = str(preferences.get("intent") or "default").lower()
    banks = [QUESTION_BANK_BY_INTENT.get(intent, QUESTION_BANK_BY_INTENT["default"])]
    if intent != "default":
        banks.append(QUESTION_BANK_BY_INTENT["default"])

    for bank in banks:
        spec = next((q for q in bank if q.key == slot), None)
        if spec is not None:
            return spec
    return None


def render_question(
    spec: QuestionSpec, preferences: dict, asked_keys: list[str]
) -> str:
    wordings = (spec.question, *spec.variants)
    if len(wordings) == 1:
        return spec.question

    indices = preferences.get("_question_variant_indices")
    if isinstance(indices, dict):
        current_index = int(indices.get(spec.key, 0) or 0)
    else:
        current_index = sum(1 for key in asked_keys if key == spec.key)
    return wordings[current_index % len(wordings)]


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
    message_conflict = " but " in normalized and (
        "petrol" in normalized and "diesel" in normalized
    )
    return has_marker_conflict or message_conflict


def _is_completion_signal(user_message: str) -> bool:
    normalized = (user_message or "").strip().lower()
    completion_markers = {
        "that's everything",
        "thats everything",
        "that's all",
        "thats all",
        "nothing else",
        "no more",
        "show recommendations",
    }
    return any(marker in normalized for marker in completion_markers)


def _sufficiency_reached(bank: list[QuestionSpec], preferences: dict) -> bool:
    required_ready = all(
        preferences.get(q.key) not in (None, "") for q in _required_slots(bank)
    )
    themes = preferences.get("extracted_themes") or []
    sentiment = str(preferences.get("sentiment") or "").strip().lower()
    has_signal_depth = len(themes) >= 1 or sentiment in {
        "positive",
        "neutral",
        "negative",
    }
    return required_ready and has_signal_depth


def select_policy_decision(
    preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int
) -> PolicyDecision:
    intent = str(preferences.get("intent") or "default").lower()
    bank = QUESTION_BANK_BY_INTENT.get(intent, QUESTION_BANK_BY_INTENT["default"])
    missing = _missing_slots(bank, preferences)

    if _has_contradiction(preferences, user_message):
        return PolicyDecision(
            stage="clarify",
            action="resolve_contradiction",
            question=CLARIFICATION_QUESTION,
        )

    if _is_answer_ambiguous(user_message, hesitation_count):
        if hesitation_count >= 3 and missing:
            return PolicyDecision(
                stage="narrow", action="recover_from_ambiguity", question=missing[0]
            )
        return PolicyDecision(
            stage="clarify", action="resolve_ambiguity", question=CLARIFICATION_QUESTION
        )

    if hesitation_count >= 2:
        monthly_q = next(
            (
                q
                for q in bank
                if q.key == "monthly_from_gbp" and preferences.get(q.key) in (None, "")
            ),
            None,
        )
        if monthly_q is not None:
            return PolicyDecision(
                stage="narrow",
                action="prioritize_budget_after_hesitation",
                question=monthly_q,
            )

    if _sufficiency_reached(bank, preferences):
        if preferences.get("summary_presented"):
            return PolicyDecision(stage="recommend", action="present_recommendations")
        return PolicyDecision(stage="summarize", action="summarize_preferences")

    missing_required = [
        q for q in _required_slots(bank) if preferences.get(q.key) in (None, "")
    ]
    if not missing_required and _is_completion_signal(user_message):
        return PolicyDecision(stage="summarize", action="summarize_preferences")
    for q in missing_required:
        if q.key not in asked_keys:
            return PolicyDecision(
                stage="discover", action="collect_required_slot", question=q
            )
    if missing_required:
        return PolicyDecision(
            stage="discover",
            action="revisit_required_slot",
            question=missing_required[0],
        )

    if missing:
        for q in missing:
            if q.key not in asked_keys:
                return PolicyDecision(
                    stage="narrow", action="collect_optional_slot", question=q
                )
        return PolicyDecision(
            stage="narrow", action="revisit_optional_slot", question=missing[0]
        )

    return PolicyDecision(stage="recommend", action="present_recommendations")


def decide_next_action(
    preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int
) -> PolicyDecision:
    decision = select_policy_decision(
        preferences, asked_keys, user_message, hesitation_count
    )
    intent = str(preferences.get("intent") or "default").lower()
    bank = QUESTION_BANK_BY_INTENT.get(intent, QUESTION_BANK_BY_INTENT["default"])
    required_complete = all(
        preferences.get(q.key) not in (None, "") for q in _required_slots(bank)
    )

    if required_complete and preferences.get("summary_presented"):
        decision = PolicyDecision(stage="recommend", action="present_recommendations")
    elif required_complete and decision.stage in {"narrow", "discover"}:
        decision = PolicyDecision(stage="summarize", action="summarize_preferences")

    if decision.question is not None:
        assistant_action = (
            "clarify_with_options" if decision.stage == "clarify" else "ask_follow_up"
        )
        return PolicyDecision(
            stage=decision.stage,
            action=decision.action,
            question=decision.question,
            assistant_action=assistant_action,
            target_slot=decision.question.key,
            reason=(decision.action or "policy_selected"),
            confidence=0.9,
            fallback_action=(
                "ask_follow_up"
                if assistant_action == "clarify_with_options"
                else "clarify_with_options"
            ),
            question_spec=decision.question,
        )

    assistant_action = (
        "present_recommendations"
        if decision.stage == "recommend"
        else "summarize_and_recommend"
    )
    return PolicyDecision(
        stage=decision.stage,
        action=decision.action,
        question=None,
        assistant_action=assistant_action,
        target_slot=None,
        reason=(decision.action or "required fields captured"),
        confidence=0.9,
        fallback_action="ask_follow_up",
        question_spec=None,
    )


def select_next_question(
    preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int
) -> QuestionSpec | None:
    return select_policy_decision(
        preferences, asked_keys, user_message, hesitation_count
    ).question
