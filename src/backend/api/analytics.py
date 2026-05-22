from __future__ import annotations

from fastapi import APIRouter

from src.backend.services.ai.conversation_orchestrator import get_session_pain_points, get_session_intelligence, aggregate_intelligence_trends

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/pain-points/{session_id}")
def session_pain_points(session_id: str):
    return get_session_pain_points(session_id)


@router.get("/intelligence/{session_id}")
def session_intelligence(session_id: str):
    return get_session_intelligence(session_id)


@router.get("/trends")
def intelligence_trends(start_date: str | None = None, end_date: str | None = None):
    return aggregate_intelligence_trends(start_date=start_date, end_date=end_date)
