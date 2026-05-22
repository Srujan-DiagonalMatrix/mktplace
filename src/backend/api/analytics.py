from __future__ import annotations

from fastapi import APIRouter

from src.backend.services.ai.conversation_orchestrator import get_session_pain_points

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/pain-points/{session_id}")
def session_pain_points(session_id: str):
    return get_session_pain_points(session_id)
