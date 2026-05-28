from __future__ import annotations

import re
import time
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.schemas.chat import ChatMessage, ChatResponse
from src.backend.core.database import get_db
from src.backend.repositories.sessions import SessionsRepository
from src.backend.services.ai.preference_extractor import extract_preferences_from_text
from src.backend.services.inventory.catalog import get_default_catalog
from src.backend.services.ai.chat_llm_orchestrator import ChatOrchestrator, PromptTemplate

from src.backend.services.ai.conversation_orchestrator import (
    create_or_get_session,
    add_message,
    update_preferences,
    get_preferences,
    set_last_question_key,
    get_last_question_key,
    set_last_question_asked_at,
    get_last_question_asked_at,
    add_asked_question_key,
    get_asked_question_keys,
    get_hesitation_count,
    increment_hesitation,
    reset_hesitation,
    extract_pain_points_for_turn,
)
from src.backend.services.ai.question_policy import decide_next_action
from src.backend.services.ai.curated_runtime_adapter import CuratedInteractionAdapter

router = APIRouter(prefix="/chat", tags=["chat"])


@lru_cache(maxsize=1)
def get_chat_orchestrator() -> ChatOrchestrator:
    return ChatOrchestrator()


_orchestrator = get_chat_orchestrator()
_curated_adapter = CuratedInteractionAdapter()

def _catalog_options(field_name: str) -> list[str]:
    try:
        catalog = get_default_catalog()
        values = {
            str(getattr(vehicle, field_name)).strip()
            for vehicle in catalog.vehicles.values()
            if getattr(vehicle, field_name, None)
        }
    except Exception:
        return []
    return sorted(values)


STATEMENTS_BY_KEY = {
    "transmission": "That makes sense. I’ll use your preferences to find vehicles that feel practical and suitable for your needs.",
    "doors": "That makes sense. I’ll use your preferences to find vehicles that feel practical and suitable for your needs.",
    "monthly_from_gbp": "Nice preference — that helps me narrow down the best matches for you much more accurately.",
    "term_months": "I like that choice. It gives us a good balance between budget, comfort, and everyday usability.",
    "employment_status": "Perfect, that’s helpful. I’ll keep your budget in mind and avoid showing options that feel unrealistic.",
}


def _parse_numeric_answer(message: str) -> float | None:
    normalized = message.strip().lower().replace(",", "")
    match = re.search(r"(?:£|gbp)?\s*(\d+(?:\.\d+)?)\s*(k|thousand)?", normalized)
    if not match:
        return None
    value = float(match.group(1))
    multiplier = 1000 if match.group(2) in {"k", "thousand"} else 1
    return value * multiplier


def _coerce_slot_answer(slot: str, message: str, extracted_value: object | None) -> object:
    numeric_value = _parse_numeric_answer(message)
    integer_slots = {"doors", "seats", "term_months", "annual_mileage_limit", "age_limit_years"}
    finance_slots = {"monthly_from_gbp", "deposit_gbp", "monthly_budget", "budget_monthly_gbp"}
    numeric_slots = integer_slots | finance_slots
    normalized = message.strip().lower()

    if slot in integer_slots and numeric_value is not None:
        return int(round(numeric_value))
    if slot in finance_slots and numeric_value is not None:
        return float(numeric_value)
    if slot == "deposit_gbp" and re.search(r"\b(no|none|zero|nothing)\b", normalized):
        return 0.0
    if slot in numeric_slots:
        return extracted_value if isinstance(extracted_value, (int, float)) else None
    return extracted_value if extracted_value not in (None, "") else message.strip()


def _has_matching_inventory(preferences: dict) -> bool:
    try:
        catalog = get_default_catalog()
        for vehicle in catalog.vehicles.values():
            if preferences.get("fuel_type") and str(getattr(vehicle, "fuel_type", "")).lower() != str(preferences["fuel_type"]).lower():
                continue
            if preferences.get("transmission") and str(getattr(vehicle, "transmission", "")).lower() != str(preferences["transmission"]).lower():
                continue
            if preferences.get("doors") and int(getattr(vehicle, "doors", 0) or 0) != int(preferences["doors"]):
                continue
            if preferences.get("seats") and int(getattr(vehicle, "seats", 0) or 0) != int(preferences["seats"]):
                continue
            return True
    except Exception:
        return True
    return False


def _build_next_reply(preferences: dict, asked_keys: list[str], user_message: str, hesitation_count: int) -> tuple[str, list[str] | None, str | None, dict | None, dict]:
    decision = decide_next_action(preferences, asked_keys=asked_keys, user_message=user_message, hesitation_count=hesitation_count)
    next_question = decision.question_spec
    if not next_question:
        reply = (
            "Great — I’ll show your recommendations now."
            if decision.assistant_action == "present_recommendations"
            else "Thanks, I’ve got enough detail to summarize your preferences and recommend suitable vehicles."
        )
        return (
            reply,
            None,
            None,
            None,
            {
                "assistant_action": decision.assistant_action,
                "target_slot": decision.target_slot,
                "decision_confidence": decision.confidence,
                "decision_reason": decision.reason,
            },
        )
    quick_replies = _catalog_options(next_question.key) if next_question.key in {"fuel_type", "transmission"} else None
    metadata = {"slot": next_question.key, "purpose": next_question.purpose, "category": next_question.category, "required": next_question.required}
    metadata.update(
        {
            "assistant_action": decision.assistant_action,
            "target_slot": decision.target_slot,
            "decision_confidence": decision.confidence,
            "decision_reason": decision.reason,
        }
    )
    return (next_question.question, quick_replies or None, next_question.key, metadata, metadata)


def _build_next_reply_from_policy(preferences: dict, policy: dict) -> tuple[str, list[str] | None, str | None, dict | None, dict]:
    action = policy.get("assistant_action")
    target_slot = policy.get("target_slot")
    question_text = policy.get("question_text")
    if action == "summarize_and_recommend" or not target_slot:
        assistant_action = "present_recommendations" if preferences.get("summary_presented") else (action or "summarize_and_recommend")
        reply = (
            "Great — I’ll show your recommendations now."
            if assistant_action == "present_recommendations"
            else "Thanks, I’ve got enough detail to summarize your preferences and recommend suitable vehicles."
        )
        decision = {
            "assistant_action": assistant_action,
            "target_slot": None,
            "decision_confidence": policy.get("confidence"),
            "decision_reason": policy.get("reason"),
        }
        return (reply, None, None, None, decision)
    quick_replies = _catalog_options(target_slot) if target_slot in {"fuel_type", "transmission"} else None
    metadata = {
        "slot": target_slot,
        "purpose": "llm_selected_policy",
        "category": "llm_policy",
        "required": True,
        "assistant_action": action,
        "target_slot": target_slot,
        "decision_confidence": policy.get("confidence"),
        "decision_reason": policy.get("reason"),
    }
    return (question_text, quick_replies or None, target_slot, metadata, metadata)


def _build_policy_decision_payload(next_question_key: str | None, question_metadata: dict | None, preferences: dict) -> dict:
    unresolved_required_slots = []
    if next_question_key and question_metadata and question_metadata.get("required"):
        unresolved_required_slots.append(next_question_key)
    return {
        "assistant_action": "ask_follow_up" if next_question_key else "complete",
        "target_slot": next_question_key,
        "unresolved_required_slots": unresolved_required_slots,
        "preferences_snapshot": preferences,
    }


@router.post("/message", response_model=ChatResponse)
def post_message(
    payload: ChatMessage,
    db: Session = Depends(get_db),
    orchestrator: ChatOrchestrator = Depends(lambda: _orchestrator),
):
    s = create_or_get_session(payload.session_id)
    if not s:
        raise HTTPException(status_code=500, detail="Failed to create session")
    session_id = s["session_id"]
    repo = SessionsRepository(db)
    persistence_enabled = True
    try:
        if not repo.get_session(session_id):
            repo.create_session(session_id=session_id, stage="chat")
    except Exception:
        persistence_enabled = False
    add_message(session_id, payload.message)
    turn_id = f"turn-{s['turn_counter']}"
    if persistence_enabled:
        created_turn = repo.create_turn(session_id=session_id, role="user", content=payload.message)
        turn_id = created_turn.turn_id
    extract_pain_points_for_turn(session_id, turn_id=turn_id, text=payload.message)
    from src.backend.services.ai.conversation_orchestrator import record_turn_intelligence
    record_turn_intelligence(session_id, turn_id=turn_id, text=payload.message)
    prefs = extract_preferences_from_text(payload.message)
    existing = get_preferences(session_id)
    last_question_key = get_last_question_key(session_id)
    if last_question_key:
        if persistence_enabled:
            repo.log_event(session_id=session_id, event_type="question_answered", stage=last_question_key, details={"answer": payload.message})
        prefs[last_question_key] = _coerce_slot_answer(
            last_question_key,
            payload.message,
            prefs.get(last_question_key),
        )
        if last_question_key in {"monthly_from_gbp", "deposit_gbp", "budget_monthly_gbp"}:
            # Ignore generic monthly budget extraction when answering explicit pricing questions.
            prefs.pop("monthly_budget", None)
        if last_question_key != "monthly_budget":
            prefs.pop("monthly_budget", None)
    update_preferences(session_id, prefs)
    current = get_preferences(session_id)
    if persistence_enabled:
        repo.create_preference_snapshot(session_id=session_id, stage="chat", payload=current)
    if not _has_matching_inventory(current):
        current.clear()
        set_last_question_key(session_id, "fuel_type")
        add_asked_question_key(session_id, "fuel_type")
        set_last_question_asked_at(session_id, time.time())
        if persistence_enabled:
            repo.log_event(session_id=session_id, event_type="unanswered_timeout_drop", stage="fuel_type")
        return ChatResponse(
            session_id=session_id,
            reply=(
                "Unfortunately, we don’t currently have any vehicles that match these criteria. "
                "Let’s review your preferences and see if we can find a suitable alternative.\n\n"
                "What type of fuel would you prefer for your next vehicle?"
            ),
            quick_replies=_catalog_options("fuel_type") or None,
        )
    normalized = payload.message.strip().lower()
    if normalized in {"maybe", "not sure", "idk", "unsure", "depends"}:
        hesitation_count = increment_hesitation(session_id)
    else:
        reset_hesitation(session_id)
        hesitation_count = get_hesitation_count(session_id)
    previous_key = last_question_key
    statement = STATEMENTS_BY_KEY.get(previous_key)
    deterministic_reply = _build_next_reply(current, asked_keys=get_asked_question_keys(session_id), user_message=payload.message, hesitation_count=hesitation_count)
    curated_priors = _curated_adapter.get_policy_priors(preferences=current, hesitation_count=hesitation_count, last_question_key=previous_key)
    policy_outcome = orchestrator.run_policy_orchestrator(session=s, user_message=payload.message)
    policy_source = "deterministic"
    deterministic_action = deterministic_reply[4].get("assistant_action")
    if (
        deterministic_action != "present_recommendations"
        and policy_outcome.used_llm
        and policy_outcome.response is not None
    ):
        selected_reply = _build_next_reply_from_policy(current, policy_outcome.response.model_dump())
        policy_source = "llm"
    else:
        selected_reply = deterministic_reply
    if statement:
        current_reply, _, next_question_key, question_metadata, decision_payload = selected_reply
        reply = f"{statement}\n\n{current_reply}"
        quick_replies = None
    else:
        reply, quick_replies, next_question_key, question_metadata, decision_payload = selected_reply
    now = time.time()
    if now - get_last_question_asked_at(session_id) < 4 and next_question_key is not None:
        reply = f"Give me a moment while I filter the latest results for you. {reply}"
    elif next_question_key is not None:
        set_last_question_asked_at(session_id, now)
        add_asked_question_key(session_id, next_question_key)
    set_last_question_key(session_id, next_question_key)
    if decision_payload.get("assistant_action") == "summarize_and_recommend":
        update_preferences(session_id, {"summary_presented": True})
        current = get_preferences(session_id)
    policy_decision = _build_policy_decision_payload(next_question_key=next_question_key, question_metadata=question_metadata, preferences=current)
    policy_decision["assistant_action"] = decision_payload.get("assistant_action") or policy_decision["assistant_action"]
    if curated_priors:
        policy_decision["curated_priors"] = [p.__dict__ for p in curated_priors]
    llm_session = dict(s)
    llm_session["preferences"] = {**current, "hesitation_count": hesitation_count}
    llm_payload = orchestrator.run(
        session=llm_session,
        user_message=payload.message,
        template=PromptTemplate.FOLLOW_UP,
        policy_decision=policy_decision,
    )
    if llm_payload.used_llm and llm_payload.response is not None:
        reply = llm_payload.response.reply
    elif persistence_enabled and llm_payload.fallback_reason is not None:
        repo.log_event(
            session_id=session_id,
            event_type="llm_fallback",
            stage=next_question_key or "completed",
            details={"reason": llm_payload.fallback_reason.value},
        )

    diagnostics = {
        "used_llm": llm_payload.used_llm,
        "fallback_reason": llm_payload.fallback_reason.value if llm_payload.fallback_reason else None,
        "model_name": orchestrator.model_name,
        "decision_source": "llm" if llm_payload.used_llm else "deterministic",
        "policy_source": policy_source,
    }

    if persistence_enabled:
        if next_question_key is not None:
            repo.log_event(session_id=session_id, event_type="question_asked", stage=next_question_key, details={"reply": reply, **diagnostics})
        else:
            repo.log_event(session_id=session_id, event_type="user_exit", stage="completed", details=diagnostics)
        repo.create_turn(session_id=session_id, role="assistant", content=reply)
        repo.update_stage(session_id, next_question_key or "completed")
    return ChatResponse(
        session_id=session_id,
        reply=reply,
        intent=current.get("intent"),
        monthly_budget=current.get("monthly_from_gbp") or current.get("monthly_budget"),
        fuel_type=current.get("fuel_type"),
        transmission=current.get("transmission"),
        seats=current.get("seats"),
        doors=current.get("doors"),
        mileage_range=current.get("mileage_range"),
        monthly_from_gbp=current.get("monthly_from_gbp"),
        deposit_gbp=current.get("deposit_gbp"),
        term_months=current.get("term_months"),
        annual_mileage_limit=current.get("annual_mileage_limit"),
        employment_status=current.get("employment_status"),
        part_exchange=current.get("part_exchange"),
        callback_opt_in=current.get("callback_opt_in"),
        quick_replies=quick_replies,
        question_metadata=question_metadata if next_question_key is not None else None,
        assistant_action=decision_payload.get("assistant_action"),
        target_slot=decision_payload.get("target_slot"),
        decision_confidence=decision_payload.get("decision_confidence"),
        decision_reason=decision_payload.get("decision_reason"),
    )
