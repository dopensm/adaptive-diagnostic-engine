"""Session API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database

from app.db.mongo import get_db
from app.models.schemas import StartSessionResponse, StudyPlanResponse, SubmitAnswerRequest, SubmitAnswerResponse, UserSession
from app.services.sessions import SessionError, get_session, start_session, submit_answer
from app.services.study_plan import generate_study_plan

router = APIRouter()


@router.post("", response_model=StartSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(database: Database = Depends(get_db)) -> StartSessionResponse:
    """Start a new adaptive testing session."""

    try:
        return start_session(database)
    except SessionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{session_id}/answers", response_model=SubmitAnswerResponse)
def submit_session_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    database: Database = Depends(get_db),
) -> SubmitAnswerResponse:
    """Submit an answer for the current question in a session."""

    try:
        return submit_answer(database, session_id, payload)
    except SessionError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.get("/{session_id}", response_model=UserSession)
def fetch_session(session_id: str, database: Database = Depends(get_db)) -> UserSession:
    """Fetch full session state and summary."""

    session = get_session(database, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    return session


@router.post("/{session_id}/study-plan", response_model=StudyPlanResponse)
def create_study_plan(session_id: str, database: Database = Depends(get_db)) -> StudyPlanResponse:
    """Generate or fetch a study plan for a completed session."""

    try:
        return generate_study_plan(database, session_id)
    except SessionError as exc:
        detail = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "not found" in detail.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=detail) from exc
