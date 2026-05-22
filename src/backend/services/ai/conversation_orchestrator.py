from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import copy
import re
import time
from datetime import datetime


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

PAIN_POINT_TAXONOMY: dict[str, tuple[tuple[str, float], ...]] = {
    "pricing_confusion": ((r"\b(confus(?:ed|ing)|don't understand|unclear|explain)\b.*\b(price|pricing|cost)\b", 0.9),),
    "apr_interest_concern": ((r"\b(apr|interest|rate|rates)\b", 0.8), (r"\btoo high|high\b.*\b(apr|interest)\b", 0.95)),
    "deposit_affordability": ((r"\bdeposit\b.*\b(can't|cannot|afford|too much|high)\b", 0.95), (r"\bafford\b.*\bdeposit\b", 0.9)),
    "term_uncertainty": ((r"\b(term|months|length|duration)\b.*\b(not sure|unsure|don't know|unclear)\b", 0.9),),
    "trust_reliability_concerns": ((r"\b(trust|reliable|reliability|scam|legit|honest)\b", 0.85),),
    "process_friction": ((r"\b(too many steps|complicated|friction|difficult process|takes too long|slow process)\b", 0.9),),
}

PAIN_POINT_CONFIDENCE_THRESHOLD = 0.78


SENTIMENT_LABEL_POSITIVE = "positive"
SENTIMENT_LABEL_NEUTRAL = "neutral"
SENTIMENT_LABEL_NEGATIVE = "negative"

SENTIMENT_RULES: dict[str, tuple[tuple[str, float], ...]] = {
    SENTIMENT_LABEL_POSITIVE: ((r"\b(great|good|love|excellent|happy|perfect|thanks|awesome)\b", 0.85),),
    SENTIMENT_LABEL_NEGATIVE: ((r"\b(worried|anxious|confused|frustrated|can'?t|cannot|too high|expensive|uncertain|unsure)\b", 0.85),),
}

THEME_RULES: dict[str, tuple[str, ...]] = {
    "budget_anxiety": ("budget", "afford", "expensive", "too high", "deposit", "monthly"),
    "ev_uncertainty": ("ev", "electric", "charging", "battery range", "range anxiety"),
    "apr_concern": ("apr", "interest", "rate"),
}

THEME_SYNONYM_MAP: dict[str, str] = {
    "cost_stress": "budget_anxiety",
    "price_worry": "budget_anxiety",
    "electric_vehicle_uncertainty": "ev_uncertainty",
    "charging_concern": "ev_uncertainty",
}


def normalize_theme_label(label: str) -> str:
    normalized = label.strip().lower().replace(" ", "_")
    return THEME_SYNONYM_MAP.get(normalized, normalized)


def classify_sentiment_for_turn(text: str) -> dict[str, Any]:
    normalized = text.strip().lower()
    if not normalized:
        return {"label": SENTIMENT_LABEL_NEUTRAL, "score": 0.0, "confidence": 0.0, "explainability": {"matched_rules": []}}

    pos_score = max((score for pattern, score in SENTIMENT_RULES[SENTIMENT_LABEL_POSITIVE] if re.search(pattern, normalized)), default=0.0)
    neg_score = max((score for pattern, score in SENTIMENT_RULES[SENTIMENT_LABEL_NEGATIVE] if re.search(pattern, normalized)), default=0.0)
    polarity = round(pos_score - neg_score, 3)
    if polarity > 0.15:
        label = SENTIMENT_LABEL_POSITIVE
        confidence = pos_score
    elif polarity < -0.15:
        label = SENTIMENT_LABEL_NEGATIVE
        confidence = neg_score
    else:
        label = SENTIMENT_LABEL_NEUTRAL
        confidence = max(pos_score, neg_score, 0.6 if normalized else 0.0)
    return {
        "label": label,
        "score": polarity,
        "confidence": round(confidence, 3),
        "explainability": {"positive_score": pos_score, "negative_score": neg_score},
    }


def extract_themes_for_turn(text: str) -> list[dict[str, Any]]:
    normalized = text.strip().lower()
    found: list[dict[str, Any]] = []
    for label, phrases in THEME_RULES.items():
        matches = [phrase for phrase in phrases if phrase in normalized]
        if matches:
            found.append({"label": label, "confidence": round(min(1.0, 0.55 + 0.1 * len(matches)), 3), "explainability": {"matched_phrases": matches}})
    return found


def record_turn_intelligence(session_id: str, turn_id: str, text: str) -> dict[str, Any]:
    s = create_or_get_session(session_id)
    sentiment = classify_sentiment_for_turn(text)
    themes = extract_themes_for_turn(text)
    normalized_themes = []
    for t in themes:
        canonical = normalize_theme_label(t["label"])
        entry = {**t, "label": canonical}
        normalized_themes.append(entry)
        agg = s["themes"].setdefault(canonical, {"label": canonical, "count": 0, "max_confidence": 0.0, "source_turn_ids": []})
        agg["count"] += 1
        agg["max_confidence"] = max(float(agg["max_confidence"]), float(t["confidence"]))
        agg["source_turn_ids"] = sorted(set(agg["source_turn_ids"] + [turn_id]))

    s["turn_intelligence"][turn_id] = {
        "turn_id": turn_id,
        "sentiment": sentiment,
        "themes": normalized_themes,
    }
    s["sentiment_summary"][sentiment["label"]] = s["sentiment_summary"].get(sentiment["label"], 0) + 1
    return s["turn_intelligence"][turn_id]


def get_session_intelligence(session_id: str) -> dict[str, Any]:
    s = create_or_get_session(session_id)
    total = sum(s["sentiment_summary"].values()) or 1
    weighted = (
        s["sentiment_summary"].get(SENTIMENT_LABEL_POSITIVE, 0) - s["sentiment_summary"].get(SENTIMENT_LABEL_NEGATIVE, 0)
    ) / total
    return {
        "session_id": session_id,
        "turn_intelligence": copy.deepcopy(s["turn_intelligence"]),
        "sentiment_summary": copy.deepcopy(s["sentiment_summary"]),
        "session_sentiment_score": round(weighted, 3),
        "themes": sorted(copy.deepcopy(list(s["themes"].values())), key=lambda t: (-t["count"], t["label"])),
    }


def aggregate_intelligence_trends(start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    from datetime import datetime
    sd = datetime.fromisoformat(start_date) if start_date else None
    ed = datetime.fromisoformat(end_date) if end_date else None
    by_date: dict[str, dict[str, Any]] = {}
    for session in _SESSIONS.values():
        for turn in session.get("messages_meta", []):
            created_at = turn["created_at"]
            if sd and created_at.date() < sd.date():
                continue
            if ed and created_at.date() > ed.date():
                continue
            key = created_at.date().isoformat()
            bucket = by_date.setdefault(key, {"sentiment": {SENTIMENT_LABEL_POSITIVE: 0, SENTIMENT_LABEL_NEUTRAL: 0, SENTIMENT_LABEL_NEGATIVE: 0}, "themes": {}})
            intel = session.get("turn_intelligence", {}).get(turn["turn_id"])
            if not intel:
                continue
            bucket["sentiment"][intel["sentiment"]["label"]] += 1
            for theme in intel["themes"]:
                bucket["themes"][theme["label"]] = bucket["themes"].get(theme["label"], 0) + 1
    return {"start_date": start_date, "end_date": end_date, "by_date": dict(sorted(by_date.items()))}


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
        "pain_points": {},
        "pain_points_by_turn": {},
        "turn_intelligence": {},
        "sentiment_summary": {SENTIMENT_LABEL_POSITIVE: 0, SENTIMENT_LABEL_NEUTRAL: 0, SENTIMENT_LABEL_NEGATIVE: 0},
        "themes": {},
        "messages_meta": [],
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
    s["turn_counter"] += 1
    s["messages_meta"].append({"turn_id": f"turn-{s['turn_counter']}", "created_at": datetime.utcnow()})


def extract_pain_points_for_turn(session_id: str, turn_id: str, text: str) -> list[dict[str, Any]]:
    s = create_or_get_session(session_id)
    normalized = text.strip().lower()
    if not normalized:
        return []

    matched: list[dict[str, Any]] = []
    for label, patterns in PAIN_POINT_TAXONOMY.items():
        confidence = 0.0
        for pattern, score in patterns:
            if re.search(pattern, normalized):
                confidence = max(confidence, score)
        if confidence < PAIN_POINT_CONFIDENCE_THRESHOLD:
            continue
        matched.append({"label": label, "confidence": confidence})

        existing = s["pain_points"].get(label)
        if existing:
            existing["confidence"] = max(float(existing["confidence"]), confidence)
            existing["last_seen_turn_id"] = turn_id
            existing["source_turn_ids"] = sorted(set(existing["source_turn_ids"] + [turn_id]))
        else:
            s["pain_points"][label] = {
                "label": label,
                "confidence": confidence,
                "source_turn_ids": [turn_id],
                "first_seen_turn_id": turn_id,
                "last_seen_turn_id": turn_id,
            }

    # De-dup labels for a turn (multi-pattern hits)
    deduped_turn = {item["label"]: item for item in matched}
    s["pain_points_by_turn"][turn_id] = list(deduped_turn.values())
    return list(deduped_turn.values())


def get_session_pain_points(session_id: str) -> dict[str, Any]:
    s = create_or_get_session(session_id)
    return {
        "session_id": session_id,
        "pain_points": sorted(copy.deepcopy(list(s.get("pain_points", {}).values())), key=lambda p: p["label"]),
        "pain_points_by_turn": copy.deepcopy(s.get("pain_points_by_turn", {})),
    }


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
