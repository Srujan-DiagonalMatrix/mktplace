from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from src.backend.models.common import Base
from src.backend.models.finance import FinanceEstimate
from src.backend.models.leads import Enquiry, LeadNote
from src.backend.models.session import CustomerSession
from src.backend.repositories.leads import LeadsRepository
from src.backend.repositories.sessions import SessionsRepository


@pytest.fixture()
def db_session():
    """Provide an isolated SQLite database for repository/model unit tests."""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _enquiry_payload(**overrides):
    payload = {
        "vehicle_id": "V1",
        "full_name": "Tester",
        "email": "t@example.com",
        "phone": "123",
    }
    payload.update(overrides)
    return payload


def test_leads_repository_create_enquiry_and_get_enquiry(db_session):
    repo = LeadsRepository(db_session)

    enquiry = repo.create_enquiry(enquiry_data=_enquiry_payload())
    db_session.commit()

    assert enquiry.enquiry_id is not None
    assert enquiry.status == "New"

    fetched = repo.get_enquiry(enquiry.enquiry_id)
    assert fetched is not None
    assert fetched.enquiry_id == enquiry.enquiry_id
    assert fetched.vehicle_id == "V1"


def test_leads_repository_list_enquiries_filters_by_status(db_session):
    repo = LeadsRepository(db_session)
    new_enquiry = repo.create_enquiry(enquiry_data=_enquiry_payload(vehicle_id="V1"))
    contacted_enquiry = repo.create_enquiry(
        enquiry_data=_enquiry_payload(
            vehicle_id="V2",
            email="second@example.com",
            status="Contacted",
        )
    )
    db_session.commit()

    all_enquiries = repo.list_enquiries(limit=10)
    contacted_enquiries = repo.list_enquiries(status="Contacted", limit=10)

    assert {enquiry.enquiry_id for enquiry in all_enquiries} == {
        new_enquiry.enquiry_id,
        contacted_enquiry.enquiry_id,
    }
    assert [enquiry.enquiry_id for enquiry in contacted_enquiries] == [contacted_enquiry.enquiry_id]


def test_leads_repository_add_note(db_session):
    repo = LeadsRepository(db_session)
    enquiry = repo.create_enquiry(enquiry_data=_enquiry_payload())

    note = repo.add_note(enquiry_id=enquiry.enquiry_id, note_text="Customer asked for PCP details")
    db_session.commit()

    assert note.note_id is not None
    assert note.enquiry_id == enquiry.enquiry_id
    assert note.note_text == "Customer asked for PCP details"
    saved_note = db_session.query(LeadNote).filter_by(note_id=note.note_id).one()
    assert saved_note.note_text == note.note_text


def test_sessions_repository_create_session_and_update_stage(db_session):
    repo = SessionsRepository(db_session)

    session = repo.create_session(stage="start")
    db_session.commit()

    assert session.session_id is not None
    assert session.stage == "start"

    updated = repo.update_stage(session.session_id, "finance")
    db_session.commit()

    assert updated is not None
    assert updated.session_id == session.session_id
    assert updated.stage == "finance"
    assert repo.get_session(session.session_id).stage == "finance"


def test_sqlalchemy_models_can_be_created(db_session):
    enquiry = Enquiry(
        enquiry_id="enq-1",
        session_id="session-1",
        vehicle_id="vehicle-1",
        full_name="Test Buyer",
        email="buyer@example.com",
        phone="07123456789",
    )
    note = LeadNote(note_id="note-1", enquiry_id="enq-1", note_text="Follow up tomorrow")
    session = CustomerSession(session_id="session-1", stage="recommendations")
    estimate = FinanceEstimate(
        estimate_id="estimate-1",
        session_id="session-1",
        vehicle_id="vehicle-1",
        list_price_gbp=25000.0,
        deposit_gbp=2500.0,
        term_months=48,
        apr_percent=8.9,
        estimated_monthly_gbp=515.25,
        disclaimer_text="Estimate only",
    )

    db_session.add_all([enquiry, note, session, estimate])
    db_session.commit()

    assert db_session.query(Enquiry).filter_by(enquiry_id="enq-1").one().full_name == "Test Buyer"
    saved_note = db_session.query(LeadNote).filter_by(note_id="note-1").one()
    saved_session = db_session.query(CustomerSession).filter_by(session_id="session-1").one()
    saved_estimate = db_session.query(FinanceEstimate).filter_by(estimate_id="estimate-1").one()

    assert saved_note.note_text == "Follow up tomorrow"
    assert saved_session.stage == "recommendations"
    assert saved_estimate.estimated_monthly_gbp == 515.25


def test_sessions_repository_conversation_artifacts_crud(db_session):
    repo = SessionsRepository(db_session)
    session = repo.create_session(session_id="s1", stage="start")
    user_turn = repo.create_turn(session_id=session.session_id, role="user", content="hello")
    assistant_turn = repo.create_turn(session_id=session.session_id, role="assistant", content="hi there")
    snapshot = repo.create_preference_snapshot(session_id=session.session_id, stage="chat", payload={"fuel_type": "diesel"}, turn_id=user_turn.turn_id)
    event = repo.log_event(session_id=session.session_id, event_type="question_asked", stage="fuel_type", details={"q": "fuel?"})
    feedback = repo.create_feedback_note(session_id=session.session_id, note_text="great flow", sentiment="positive")
    db_session.commit()

    assert user_turn.sequence_id == 1
    assert assistant_turn.sequence_id == 2
    assert repo.list_turns(session.session_id)[0].turn_id == user_turn.turn_id
    assert snapshot.snapshot_id is not None
    assert repo.list_events(session.session_id)[0].event_id == event.event_id
    assert feedback.feedback_id is not None


def test_turn_order_integrity(db_session):
    repo = SessionsRepository(db_session)
    repo.create_session(session_id="s2", stage="start")
    t1 = repo.create_turn(session_id="s2", role="user", content="first")
    t2 = repo.create_turn(session_id="s2", role="assistant", content="second")
    db_session.commit()
    ordered = repo.list_turns("s2")
    assert [t.sequence_id for t in ordered] == [1, 2]
    assert t1.created_at <= t2.created_at


def test_invalid_payload_handling(db_session):
    repo = SessionsRepository(db_session)
    repo.create_session(session_id="s3", stage="start")
    with pytest.raises(ValueError):
        repo.create_turn(session_id="s3", role="user", content="")
    with pytest.raises(ValueError):
        repo.create_feedback_note(session_id="s3", note_text="")


def test_dropoff_attribution_stage_captured(db_session):
    repo = SessionsRepository(db_session)
    repo.create_session(session_id="s4", stage="chat")
    ev = repo.log_event(session_id="s4", event_type="unanswered_timeout_drop", stage="term_months")
    db_session.commit()
    loaded = repo.list_events("s4")
    assert loaded[-1].event_id == ev.event_id
    assert loaded[-1].stage == "term_months"


def test_enquiry_api_queues_payload_when_database_is_unavailable(monkeypatch, tmp_path):
    fastapi_module = pytest.importorskip("fastapi")
    testclient_module = pytest.importorskip("fastapi.testclient")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    from src.backend.api import enquiries as enquiries_api

    test_app = fastapi_module.FastAPI()
    test_app.include_router(enquiries_api.router)
    offline_queue = tmp_path / "offline_enquiries.jsonl"

    class UnavailableRepo:
        def create_enquiry(self, *, enquiry_data: dict):
            raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(enquiries_api, "OFFLINE_QUEUE", offline_queue)
    test_app.dependency_overrides[enquiries_api._get_repo] = lambda: UnavailableRepo()

    try:
        response = testclient_module.TestClient(test_app).post(
            "/enquiries/",
            json=_enquiry_payload(),
        )
    finally:
        test_app.dependency_overrides.pop(enquiries_api._get_repo, None)

    assert response.status_code == 202
    assert response.json() == {"detail": "Enquiry received and queued (DB unavailable)"}
    assert offline_queue.parent == tmp_path
    assert json.loads(offline_queue.read_text(encoding="utf-8")) == _enquiry_payload()
