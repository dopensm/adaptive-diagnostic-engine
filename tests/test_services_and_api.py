"""Tests for seeding, session flow, study plans, and API endpoints."""

from fastapi.testclient import TestClient

from app.db.mongo import get_db
from app.main import create_app
from app.models.schemas import SubmitAnswerRequest
from app.services.seeding import seed_questions
from app.services.sessions import get_session, start_session, submit_answer
from app.services.study_plan import generate_study_plan
from tests.fakes import FakeDatabase


def seed_fake_db() -> FakeDatabase:
    database = FakeDatabase()
    seed_questions(database)
    return database


def test_seed_is_idempotent() -> None:
    database = FakeDatabase()
    first = seed_questions(database)
    second = seed_questions(database)
    assert first.inserted_count >= 20
    assert second.inserted_count == 0
    assert second.updated_count == first.total_questions
    assert second.total_questions == first.total_questions


def test_start_session_returns_first_question() -> None:
    database = seed_fake_db()
    response = start_session(database)
    assert response.session_id
    assert response.question.question_id
    assert response.remaining_questions == 9


def test_submit_answer_completes_session_after_limit() -> None:
    database = seed_fake_db()
    start_response = start_session(database)
    session = get_session(database, start_response.session_id)
    assert session is not None

    current_question_id = start_response.question.question_id
    for _ in range(session.question_limit):
        question = database["questions"].find_one({"question_id": current_question_id})
        result = submit_answer(
            database,
            start_response.session_id,
            SubmitAnswerRequest(question_id=current_question_id, selected_answer=question["correct_answer"]),
        )
        if result.next_question is None:
            break
        current_question_id = result.next_question.question_id

    final_session = get_session(database, start_response.session_id)
    assert final_session is not None
    assert final_session.status == "completed"
    assert final_session.summary is not None
    assert final_session.summary.total_questions == session.question_limit


def test_study_plan_uses_fallback_without_api_key() -> None:
    database = seed_fake_db()
    start_response = start_session(database)
    current_question_id = start_response.question.question_id
    session = get_session(database, start_response.session_id)
    assert session is not None

    for _ in range(session.question_limit):
        result = submit_answer(
            database,
            start_response.session_id,
            SubmitAnswerRequest(question_id=current_question_id, selected_answer="Z"),
        )
        if result.next_question is None:
            break
        current_question_id = result.next_question.question_id

    study_plan = generate_study_plan(database, start_response.session_id)
    assert study_plan.is_fallback is True
    assert study_plan.provider_used == "fallback"
    assert len(study_plan.study_plan_steps) == 3


def test_api_session_flow_and_study_plan() -> None:
    database = seed_fake_db()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: database
    client = TestClient(app)

    start_response = client.post("/sessions")
    assert start_response.status_code == 201
    payload = start_response.json()
    session_id = payload["session_id"]
    question_id = payload["question"]["question_id"]

    current_question_id = question_id
    for _ in range(10):
        answer_response = client.post(
            f"/sessions/{session_id}/answers",
            json={"question_id": current_question_id, "selected_answer": "A"},
        )
        assert answer_response.status_code == 200
        answer_payload = answer_response.json()
        if answer_payload["next_question"] is None:
            break
        current_question_id = answer_payload["next_question"]["question_id"]

    session_response = client.get(f"/sessions/{session_id}")
    assert session_response.status_code == 200
    assert session_response.json()["status"] == "completed"

    study_plan_response = client.post(f"/sessions/{session_id}/study-plan")
    assert study_plan_response.status_code == 200
    plan_payload = study_plan_response.json()
    assert plan_payload["session_id"] == session_id
    assert len(plan_payload["study_plan_steps"]) == 3
