from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter

from src.backend.services.ai.conversation_orchestrator import (
    SENTIMENT_LABEL_NEGATIVE,
    aggregate_intelligence_trends,
    get_session_intelligence,
    get_session_pain_points,
    summarize_analytics_dashboard,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/pain-points/{session_id}")
def session_pain_points(
    session_id: str,
    window: str = "7d",
    frequency_weight: float | None = None,
    severity_weight: float | None = None,
    impact_weight: float | None = None,
    debug: bool = False,
):
    override = None
    if any(v is not None for v in (frequency_weight, severity_weight, impact_weight)):
        override = {
            "frequency": frequency_weight or 0.0,
            "severity": severity_weight or 0.0,
            "impact": impact_weight or 0.0,
        }
    return get_session_pain_points(session_id, window=window, override_weights=override, debug=debug)


@router.get("/intelligence/{session_id}")
def session_intelligence(session_id: str):
    return get_session_intelligence(session_id)


@router.get("/trends")
def intelligence_trends(start_date: str | None = None, end_date: str | None = None):
    return aggregate_intelligence_trends(start_date=start_date, end_date=end_date)


@router.get('/dashboard')
def analytics_dashboard(
    start_date: str | None = None,
    end_date: str | None = None,
    vehicle_type: str | None = None,
    fuel_type: str | None = None,
    stage: str | None = None,
):
    return summarize_analytics_dashboard(
        start_date=start_date,
        end_date=end_date,
        vehicle_type=vehicle_type,
        fuel_type=fuel_type,
        stage=stage,
    )
