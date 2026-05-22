from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.schemas.chat import ChatMessage, ChatResponse
from src.backend.core.database import get_db
from src.backend.repositories.sessions import SessionsRepository
from src.backend.services.ai.preference_extractor import extract_preferences_from_text
from src.backend.services.inventory.catalog import get_default_catalog
from src.backend.services.ai.conversation_orchestrator import (
    create_or_get_session,
    add_message,
    update_preferences,
    get_preferences,
    set_last_question_key,
    get_last_question_key,
    set_last_question_asked_at,
    get_last_question_asked_at,
)

router = APIRouter(prefix="/chat", tags=["chat"])

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


QUESTION_SEQUENCE: list[tuple[str, str]] = [
    ("fuel_type", "What type of fuel would you prefer for your next vehicle?"),
    ("transmission", "Do you have a preferred transmission type?"),
    ("mileage_range", "What mileage range would you ideally like?"),
    ("doors", "How many doors would you prefer?"),
    ("seats", "How many seats do you need?"),
    ("monthly_from_gbp", "What monthly budget would you like to stay within?"),
    ("deposit_gbp", "How much deposit would you ideally like to put down?"),
    ("term_months", "What finance term would suit you best?"),
    ("annual_mileage_limit", "Roughly how many miles do you expect to drive each year?"),
    ("employment_status", "What is your current employment status?"),
    ("part_exchange", "Do you have a vehicle you would like to part exchange?"),
    ("callback_opt_in", "When would you ideally like to place your order, I can arrange a callback?"),
]

STATEMENTS_BY_KEY = {
    "transmission": "That makes sense. I’ll use your preferences to find vehicles that feel practical and suitable for your needs.",
    "doors": "That makes sense. I’ll use your preferences to find vehicles that feel practical and suitable for your needs.",
    "monthly_from_gbp": "Nice preference — that helps me narrow down the best matches for you much more accurately.",
    "term_months": "I like that choice. It gives us a good balance between budget, comfort, and everyday usability.",
    "employment_status": "Perfect, that’s helpful. I’ll keep your budget in mind and avoid showing options that feel unrealistic.",
}


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


def _build_next_reply(preferences: dict) -> tuple[str, list[str] | None, str | None]:
    if not preferences.get("fuel_type"):
        fuel_options = _catalog_options("fuel_type")
        return QUESTION_SEQUENCE[0][1], fuel_options or None, "fuel_type"
    if not preferences.get("transmission"):
        transmission_options = _catalog_options("transmission")
        return QUESTION_SEQUENCE[1][1], transmission_options or None, "transmission"
    for key, question in QUESTION_SEQUENCE[2:]:
        if preferences.get(key) in (None, ""):
            return question, None, key

    return (
        "It was a great experience talking to you conversation, Thank you!",
        None,
        None,
    )


@router.post("/message", response_model=ChatResponse)
def post_message(payload: ChatMessage, db: Session = Depends(get_db)):
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
    if persistence_enabled:
        repo.create_turn(session_id=session_id, role="user", content=payload.message)
    prefs = extract_preferences_from_text(payload.message)
    existing = get_preferences(session_id)
    last_question_key = get_last_question_key(session_id)
    if last_question_key:
        if persistence_enabled:
            repo.log_event(session_id=session_id, event_type="question_answered", stage=last_question_key, details={"answer": payload.message})
        prefs[last_question_key] = prefs.get(last_question_key) or payload.message.strip()
        if last_question_key in {"doors", "seats", "term_months", "annual_mileage_limit"} and str(payload.message).strip().isdigit():
            prefs[last_question_key] = int(str(payload.message).strip())
        if last_question_key in {"monthly_from_gbp", "deposit_gbp"}:
            digits = "".join(ch for ch in payload.message if ch.isdigit())
            if digits:
                prefs[last_question_key] = float(digits)
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
    previous_key = last_question_key
    statement = STATEMENTS_BY_KEY.get(previous_key)
    if statement:
        current_reply, _, _ = _build_next_reply(current)
        reply = f"{statement}\n\n{current_reply}"
        next_question_key = _build_next_reply(current)[2]
        quick_replies = None
    else:
        reply, quick_replies, next_question_key = _build_next_reply(current)
    now = time.time()
    if now - get_last_question_asked_at(session_id) < 4 and next_question_key is not None:
        reply = f"Give me a moment while I filter the latest results for you. {reply}"
    elif next_question_key is not None:
        set_last_question_asked_at(session_id, now)
    set_last_question_key(session_id, next_question_key)
    if persistence_enabled:
        if next_question_key is not None:
            repo.log_event(session_id=session_id, event_type="question_asked", stage=next_question_key, details={"reply": reply})
        else:
            repo.log_event(session_id=session_id, event_type="user_exit", stage="completed")
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
    )
