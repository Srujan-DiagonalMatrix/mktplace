from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from typing import List

from src.backend.core.database import get_db
from src.backend.models.leads import Enquiry
from src.backend.models.session import ConversationTurn, PreferenceSnapshot, SessionEvent, FeedbackNote


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/flush_offline")
def flush_offline(x_admin_token: str | None = Header(None)):
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # run the flush script
    from src.backend.scripts.flush_offline_enquiries import flush_queue
    try:
        flush_queue()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/enquiries", response_model=List[dict])
def list_enquiries(db=Depends(get_db), page: int = 1, limit: int = 50, x_admin_token: str | None = Header(None)):
    # simple admin token check
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        q = db.query(Enquiry).order_by(Enquiry.created_at.desc())
        items = q.offset((page - 1) * limit).limit(limit).all()
        return [
            {"enquiry_id": e.enquiry_id, "full_name": e.full_name, "email": e.email, "status": e.status}
            for e in items
        ]
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.post("/enquiries/{enquiry_id}/status")
def update_enquiry_status(enquiry_id: str, status: str, db=Depends(get_db), x_admin_token: str | None = Header(None)):
    # auth check
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        e = db.query(Enquiry).filter(Enquiry.enquiry_id == enquiry_id).one_or_none()
        if not e:
            raise HTTPException(status_code=404, detail="Enquiry not found")
        e.status = status
        db.add(e)
        db.commit()
        return {"enquiry_id": enquiry_id, "status": status}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@router.get("/conversations/{session_id}/turns", response_model=List[dict])
def conversation_turns(session_id: str, db=Depends(get_db), x_admin_token: str | None = Header(None)):
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = db.query(ConversationTurn).filter(ConversationTurn.session_id == session_id).order_by(ConversationTurn.sequence_id.asc()).all()
    return [{"turn_id": r.turn_id, "sequence_id": r.sequence_id, "role": r.role, "content": r.content, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/conversations/{session_id}/events", response_model=List[dict])
def conversation_events(session_id: str, db=Depends(get_db), x_admin_token: str | None = Header(None)):
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = db.query(SessionEvent).filter(SessionEvent.session_id == session_id).order_by(SessionEvent.created_at.asc()).all()
    return [{"event_id": r.event_id, "event_type": r.event_type, "stage": r.stage, "details_json": r.details_json, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/conversations/{session_id}/snapshots", response_model=List[dict])
def conversation_snapshots(session_id: str, db=Depends(get_db), x_admin_token: str | None = Header(None)):
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = db.query(PreferenceSnapshot).filter(PreferenceSnapshot.session_id == session_id).order_by(PreferenceSnapshot.created_at.asc()).all()
    return [{"snapshot_id": r.snapshot_id, "stage": r.stage, "payload_json": r.payload_json, "turn_id": r.turn_id, "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/conversations/{session_id}/feedback", response_model=List[dict])
def conversation_feedback(session_id: str, db=Depends(get_db), x_admin_token: str | None = Header(None)):
    from src.shared.config.settings import get_settings
    settings = get_settings()
    admin_token = getattr(settings, "admin_token", None) or ""
    if admin_token and x_admin_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    rows = db.query(FeedbackNote).filter(FeedbackNote.session_id == session_id).order_by(FeedbackNote.created_at.asc()).all()
    return [{"feedback_id": r.feedback_id, "note_text": r.note_text, "sentiment": r.sentiment, "created_at": r.created_at.isoformat()} for r in rows]
