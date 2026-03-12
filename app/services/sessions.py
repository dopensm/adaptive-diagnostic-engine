"""Session lifecycle service."""

from datetime import datetime, timezone
from uuid import uuid4

from pymongo.database import Database

from app.config import Settings, get_settings
from app.models.schemas import (
    QuestionRecord,
    SessionResponseRecord,
    StartSessionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    UserSession,
)
from app.services.adaptive_engine import (
    build_session_summary,
    select_next_question,
    to_public_question,
    update_ability_score,
)


class SessionError(Exception):
    """Raised when session operations cannot be completed."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _questions_collection(database: Database):
    return database["questions"]


def _sessions_collection(database: Database):
    return database["user_sessions"]


def _load_questions(database: Database) -> list[QuestionRecord]:
    documents = _questions_collection(database).find({}, {"_id": 0})
    return [QuestionRecord.model_validate(document) for document in documents]


def _load_question_by_id(database: Database, question_id: str) -> QuestionRecord | None:
    document = _questions_collection(database).find_one({"question_id": question_id}, {"_id": 0})
    if not document:
        return None
    return QuestionRecord.model_validate(document)


def get_session(database: Database, session_id: str) -> UserSession | None:
    """Load a stored session by ID."""

    document = _sessions_collection(database).find_one({"session_id": session_id}, {"_id": 0})
    if not document:
        return None
    return UserSession.model_validate(document)


def start_session(database: Database, settings: Settings | None = None) -> StartSessionResponse:
    """Create a new adaptive quiz session and return the first question."""

    resolved_settings = settings or get_settings()
    questions = _load_questions(database)
    if not questions:
        raise SessionError("Question bank is empty. Seed questions before starting a session.")

    session_id = str(uuid4())
    first_question = select_next_question(questions, [], resolved_settings.baseline_ability)
    if first_question is None:
        raise SessionError("No eligible question is available to start the session.")

    now = _utcnow()
    session = UserSession(
        session_id=session_id,
        status="in_progress",
        ability_score=resolved_settings.baseline_ability,
        asked_question_ids=[first_question.question_id],
        responses=[],
        question_limit=resolved_settings.test_question_limit,
        summary=None,
        created_at=now,
        updated_at=now,
    )
    _sessions_collection(database).insert_one(session.model_dump(mode="python"))

    return StartSessionResponse(
        session_id=session_id,
        ability_score=session.ability_score,
        question=to_public_question(first_question),
        remaining_questions=max(session.question_limit - 1, 0),
    )


def submit_answer(
    database: Database,
    session_id: str,
    payload: SubmitAnswerRequest,
    settings: Settings | None = None,
) -> SubmitAnswerResponse:
    """Validate a submitted answer, update ability, and return next state."""

    resolved_settings = settings or get_settings()
    session = get_session(database, session_id)
    if session is None:
        raise SessionError("Session not found.")
    if session.status == "completed":
        raise SessionError("Session is already completed.")
    if payload.question_id not in session.asked_question_ids:
        raise SessionError("Question does not belong to the active session.")
    if any(response.question_id == payload.question_id for response in session.responses):
        raise SessionError("Question has already been answered.")

    question = _load_question_by_id(database, payload.question_id)
    if question is None:
        raise SessionError("Question not found.")

    ability_before = session.ability_score
    is_correct = payload.selected_answer == question.correct_answer
    ability_after = update_ability_score(
        current_ability=ability_before,
        question_difficulty=question.difficulty,
        is_correct=is_correct,
        settings=resolved_settings,
    )

    answered_at = _utcnow()
    response_record = {
        "question_id": question.question_id,
        "selected_answer": payload.selected_answer,
        "correct_answer": question.correct_answer,
        "is_correct": is_correct,
        "difficulty": question.difficulty,
        "topic": question.topic,
        "ability_before": ability_before,
        "ability_after": ability_after,
        "answered_at": answered_at,
    }
    session.responses.append(SessionResponseRecord.model_validate(response_record))
    session.ability_score = ability_after
    session.updated_at = answered_at

    questions = _load_questions(database)
    next_question = None
    if len(session.responses) >= session.question_limit:
        session.status = "completed"
    else:
        next_question = select_next_question(questions, session.asked_question_ids, session.ability_score)
        if next_question is None:
            session.status = "completed"
        else:
            session.asked_question_ids.append(next_question.question_id)

    if session.status == "completed":
        session.summary, _ = build_session_summary(session.responses, session.ability_score, session.session_id)

    _sessions_collection(database).update_one(
        {"session_id": session.session_id},
        {"$set": session.model_dump(mode="python")},
    )

    remaining_questions = max(session.question_limit - len(session.responses) - (1 if next_question else 0), 0)
    return SubmitAnswerResponse(
        is_correct=is_correct,
        ability_score=session.ability_score,
        session_status=session.status,
        remaining_questions=remaining_questions,
        next_question=to_public_question(next_question) if next_question else None,
        summary=session.summary,
    )
