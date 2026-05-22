from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import copy
import time


CANONICAL_PREFERENCE_SCHEMA: dict[str, type] = {
    "budget_monthly_gbp": (int, float),
    "deposit_gbp": (int, float),
    "term_months": int,
    "fuel_type": str,
    "vehicle_type": str,
    "concerns": list,
    "transmission": str,
    "doors": int,
    "seats": int,
    "mileage_range": str,
    "annual_mileage_limit": int,
    "employment_status": str,
    "part_exchange": str,
    "callback_opt_in": str,
    "intent": str,
    "monthly_budget": (int, float),
    "monthly_from_gbp": (int, float),
    "body_type": str,
    "family_size": int,
}


def _infer_confidence(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 0.9
    if isinstance(value, (int, float)):
        return 0.95
    if isinstance(value, str):
        length = len(value.strip())
        if length <= 2:
            return 0.4
        if length <= 6:
            return 0.75
        return 0.85
    if isinstance(value, list):
        return 0.8 if value else 0.0
    return 0.7


def _normalize_key(key: str) -> str:
    aliases = {
        "budget": "budget_monthly_gbp",
        "monthly_budget": "budget_monthly_gbp",
        "monthly_from_gbp": "budget_monthly_gbp",
        "body_type": "vehicle_type",
    }
    return aliases.get(key, key)


@dataclass
class MemoryValue:
    value: Any
    confidence: float
    source_turn: int
    updated_at: float


# Minimal in-memory orchestrator for sessions (demo-only)
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _new_session(session_id: str) -> Dict[str, Any]:
    return {
        "session_id": session_id,
        "preferences": {},
        "memory": {},
        "messages": [],
        "turn_counter": 0,
        "memory_snapshots": [],
        "last_question_key": None,
        "last_question_asked_at": 0.0,
        "asked_question_keys": [],
        "hesitation_count": 0,
    }


def create_or_get_session(session_id: str | None, resume: bool = True) -> Dict[str, Any]:
    if session_id and resume and session_id in _SESSIONS:
        return _SESSIONS[session_id]
    sid = session_id or "sess-" + str(len(_SESSIONS) + 1)
    if sid not in _SESSIONS:
        _SESSIONS[sid] = _new_session(sid)
    return _SESSIONS[sid]


def add_message(session_id: str, message: str) -> None:
    s = create_or_get_session(session_id)
    s["messages"].append(message)


def _set_memory_value(session: Dict[str, Any], key: str, value: Any, confidence: float) -> None:
    if key not in CANONICAL_PREFERENCE_SCHEMA:
        return
    session["memory"][key] = {
        "value": value,
        "confidence": max(0.0, min(1.0, confidence)),
        "source_turn": session["turn_counter"],
        "updated_at": time.time(),
    }


def update_preferences(session_id: str, prefs: Dict[str, Any], overwrite: bool = True, min_confidence: float = 0.5) -> None:
    s = create_or_get_session(session_id)
    s["turn_counter"] += 1
    for raw_key, value in prefs.items():
        key = _normalize_key(raw_key)
        if key not in CANONICAL_PREFERENCE_SCHEMA:
            continue
        incoming_conf = _infer_confidence(value)
        if incoming_conf < min_confidence:
            continue
        existing = s["memory"].get(key)
        if not existing:
            _set_memory_value(s, key, value, incoming_conf)
            continue
        # Conflict resolution: keep higher confidence, then prefer newer value when overwrite enabled.
        if incoming_conf > float(existing.get("confidence", 0)):
            _set_memory_value(s, key, value, incoming_conf)
        elif overwrite and incoming_conf == float(existing.get("confidence", 0)) and existing.get("value") != value:
            _set_memory_value(s, key, value, incoming_conf)

    s["preferences"] = {k: v["value"] for k, v in s["memory"].items()}
    budget_value = s["preferences"].get("budget_monthly_gbp")
    if budget_value is not None:
        s["preferences"]["monthly_budget"] = budget_value
        s["preferences"]["monthly_from_gbp"] = budget_value
    vehicle_type = s["preferences"].get("vehicle_type")
    if vehicle_type is not None:
        s["preferences"]["body_type"] = vehicle_type
    persist_memory_snapshot(session_id, reason="turn_update")


def get_preferences(session_id: str) -> Dict[str, Any]:
    s = create_or_get_session(session_id)
    return s.get("preferences", {})


def get_memory(session_id: str) -> Dict[str, Dict[str, Any]]:
    s = create_or_get_session(session_id)
    return copy.deepcopy(s.get("memory", {}))


def persist_memory_snapshot(session_id: str, reason: str = "manual") -> dict[str, Any]:
    s = create_or_get_session(session_id)
    snapshot = {
        "turn": s["turn_counter"],
        "reason": reason,
        "created_at": time.time(),
        "preferences": copy.deepcopy(s.get("preferences", {})),
        "memory": copy.deepcopy(s.get("memory", {})),
    }
    s["memory_snapshots"].append(snapshot)
    return snapshot


def get_memory_snapshots(session_id: str) -> list[dict[str, Any]]:
    s = create_or_get_session(session_id)
    return copy.deepcopy(s.get("memory_snapshots", []))


def get_context_preferences(session_id: str, relevant_keys: list[str] | None = None) -> Dict[str, Any]:
    s = create_or_get_session(session_id)
    latest = s.get("preferences", {})
    if not relevant_keys:
        return copy.deepcopy(latest)
    normalized = {_normalize_key(k) for k in relevant_keys}
    return {k: v for k, v in latest.items() if k in normalized}


def set_last_question_key(session_id: str, key: str | None) -> None:
    s = create_or_get_session(session_id)
    s["last_question_key"] = key


def get_last_question_key(session_id: str) -> str | None:
    s = create_or_get_session(session_id)
    return s.get("last_question_key")


def set_last_question_asked_at(session_id: str, timestamp: float | None = None) -> None:
    s = create_or_get_session(session_id)
    s["last_question_asked_at"] = timestamp if timestamp is not None else time.time()


def get_last_question_asked_at(session_id: str) -> float:
    s = create_or_get_session(session_id)
    return float(s.get("last_question_asked_at", 0.0))


def add_asked_question_key(session_id: str, key: str) -> None:
    s = create_or_get_session(session_id)
    keys = s.setdefault("asked_question_keys", [])
    if key and key not in keys:
        keys.append(key)


def get_asked_question_keys(session_id: str) -> list[str]:
    s = create_or_get_session(session_id)
    return list(s.get("asked_question_keys", []))


def increment_hesitation(session_id: str) -> int:
    s = create_or_get_session(session_id)
    s["hesitation_count"] = int(s.get("hesitation_count", 0)) + 1
    return s["hesitation_count"]


def reset_hesitation(session_id: str) -> None:
    s = create_or_get_session(session_id)
    s["hesitation_count"] = 0


def get_hesitation_count(session_id: str) -> int:
    s = create_or_get_session(session_id)
    return int(s.get("hesitation_count", 0))
