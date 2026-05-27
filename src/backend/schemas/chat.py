from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    session_id: Optional[str] = None
    message: str


class PreferenceExtractionResponse(BaseModel):
    intent: Optional[str] = None
    monthly_budget: Optional[float] = None
    fuel_type: Optional[str] = None
    body_type: Optional[str] = None
    transmission: Optional[str] = None
    family_size: Optional[int] = None
    doors: Optional[int] = None
    seats: Optional[int] = None
    mileage_range: Optional[str] = None
    monthly_from_gbp: Optional[float] = None
    deposit_gbp: Optional[float] = None
    term_months: Optional[int] = None
    annual_mileage_limit: Optional[int] = None
    employment_status: Optional[str] = None
    part_exchange: Optional[str] = None
    callback_opt_in: Optional[str] = None


class ChatResponse(PreferenceExtractionResponse):
    session_id: str
    reply: str
    quick_replies: Optional[list[str]] = None
    question_metadata: Optional[dict] = None
    assistant_action: Optional[str] = None
    target_slot: Optional[str] = None
    decision_confidence: Optional[float] = None
    decision_reason: Optional[str] = None
    filters_applied: bool = True
    next_question_delay_seconds: int = 2
