from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from src.backend.models.common import Base


class CustomerSession(Base):
    __tablename__ = "customer_sessions"

    session_id = Column(String, primary_key=True)
    stage = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    turn_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("customer_sessions.session_id"), nullable=False, index=True)
    sequence_id = Column(Integer, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PreferenceSnapshot(Base):
    __tablename__ = "preference_snapshots"

    snapshot_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("customer_sessions.session_id"), nullable=False, index=True)
    turn_id = Column(String, ForeignKey("conversation_turns.turn_id"), nullable=True)
    stage = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SessionEvent(Base):
    __tablename__ = "session_events"

    event_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("customer_sessions.session_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    stage = Column(String, nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class FeedbackNote(Base):
    __tablename__ = "feedback_notes"

    feedback_id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("customer_sessions.session_id"), nullable=False, index=True)
    note_text = Column(Text, nullable=False)
    sentiment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
