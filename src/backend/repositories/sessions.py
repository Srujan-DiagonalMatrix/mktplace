from __future__ import annotations

from typing import Optional
from uuid import uuid4
import json
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.backend.models.session import CustomerSession, ConversationTurn, PreferenceSnapshot, SessionEvent, FeedbackNote


class SessionsRepository:
    """Repository for customer sessions."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, *, session_id: Optional[str] = None, stage: str = "start") -> CustomerSession:
        if not session_id:
            session_id = str(uuid4())
        s = CustomerSession(session_id=session_id, stage=stage)
        self.db.add(s)
        self.db.flush()
        return s

    def get_session(self, session_id: str) -> Optional[CustomerSession]:
        return self.db.query(CustomerSession).filter(CustomerSession.session_id == session_id).one_or_none()

    def update_stage(self, session_id: str, new_stage: str) -> Optional[CustomerSession]:
        s = self.get_session(session_id)
        if not s:
            return None
        s.stage = new_stage
        self.db.add(s)
        self.db.flush()
        return s

    def create_turn(self, *, session_id: str, role: str, content: str) -> ConversationTurn:
        if not content:
            raise ValueError("content cannot be empty")
        next_sequence = (
            self.db.query(func.max(ConversationTurn.sequence_id))
            .filter(ConversationTurn.session_id == session_id)
            .scalar()
            or 0
        ) + 1
        turn = ConversationTurn(
            turn_id=str(uuid4()),
            session_id=session_id,
            sequence_id=next_sequence,
            role=role,
            content=content,
        )
        self.db.add(turn)
        self.db.flush()
        return turn

    def list_turns(self, session_id: str) -> list[ConversationTurn]:
        return (
            self.db.query(ConversationTurn)
            .filter(ConversationTurn.session_id == session_id)
            .order_by(ConversationTurn.sequence_id.asc(), ConversationTurn.created_at.asc())
            .all()
        )

    def create_preference_snapshot(self, *, session_id: str, stage: str, payload: dict, turn_id: str | None = None) -> PreferenceSnapshot:
        snap = PreferenceSnapshot(
            snapshot_id=str(uuid4()),
            session_id=session_id,
            turn_id=turn_id,
            stage=stage,
            payload_json=json.dumps(payload),
        )
        self.db.add(snap)
        self.db.flush()
        return snap

    def log_event(self, *, session_id: str, event_type: str, stage: str, details: dict | None = None) -> SessionEvent:
        event = SessionEvent(
            event_id=str(uuid4()),
            session_id=session_id,
            event_type=event_type,
            stage=stage,
            details_json=json.dumps(details) if details is not None else None,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def create_feedback_note(self, *, session_id: str, note_text: str, sentiment: str | None = None) -> FeedbackNote:
        if not note_text:
            raise ValueError("note_text cannot be empty")
        note = FeedbackNote(feedback_id=str(uuid4()), session_id=session_id, note_text=note_text, sentiment=sentiment)
        self.db.add(note)
        self.db.flush()
        return note

    def list_events(self, session_id: str) -> list[SessionEvent]:
        return self.db.query(SessionEvent).filter(SessionEvent.session_id == session_id).order_by(SessionEvent.created_at.asc()).all()
