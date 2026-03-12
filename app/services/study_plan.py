"""Study-plan generation service."""

from datetime import datetime, timezone

from pymongo.database import Database

from app.config import Settings, get_settings
from app.models.schemas import PerformanceSummary, StoredStudyPlan, StudyPlanResponse
from app.services.adaptive_engine import build_session_summary
from app.services.sessions import SessionError, get_session


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sessions_collection(database: Database):
    return database["user_sessions"]


def _fallback_steps(summary: PerformanceSummary) -> list[str]:
    weak_topic_text = ", ".join(summary.weakest_topics) if summary.weakest_topics else "your broad accuracy pattern"
    return [
        f"Review foundational concepts in {weak_topic_text} and rewrite one takeaway note for each missed idea.",
        f"Practice 8 to 10 questions near difficulty {summary.highest_difficulty_reached:.2f} with a timer, then check every error for pattern and cause.",
        "End with one mixed mini-set across all topics and record whether mistakes came from concept gaps, misreading, or time pressure.",
    ]


def _build_performance_summary(session_id: str, database: Database) -> PerformanceSummary:
    session = get_session(database, session_id)
    if session is None:
        raise SessionError("Session not found.")
    if session.status != "completed":
        raise SessionError("Study plan is only available after session completion.")
    if session.summary is None:
        summary, performance_summary = build_session_summary(session.responses, session.ability_score, session.session_id)
        session.summary = summary
        _sessions_collection(database).update_one(
            {"session_id": session.session_id},
            {"$set": {"summary": summary.model_dump(mode="python"), "updated_at": _utcnow()}},
        )
        return performance_summary

    return PerformanceSummary(
        session_id=session.session_id,
        ability_score=session.ability_score,
        total_questions=session.summary.total_questions,
        correct_answers=session.summary.correct_answers,
        incorrect_answers=session.summary.incorrect_answers,
        highest_difficulty_reached=session.summary.highest_difficulty_reached,
        weakest_topics=session.summary.weakest_topics,
        topic_breakdown=session.summary.topic_breakdown,
    )


def _generate_openai_plan(summary: PerformanceSummary, settings: Settings) -> list[str] | None:
    if not settings.openai_api_key:
        return None

    try:
        from openai import OpenAI
    except Exception:
        return None

    prompt = (
        "You are generating a concise 3-step GRE study plan. "
        "Return exactly 3 short numbered steps tailored to this performance summary:\n"
        f"{summary.model_dump_json(indent=2)}"
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=prompt,
    )
    text = getattr(response, "output_text", "").strip()
    if not text:
        return None

    steps = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        cleaned = cleaned.removeprefix("1. ").removeprefix("2. ").removeprefix("3. ").strip()
        steps.append(cleaned)
    unique_steps = [step for step in steps if step]
    if len(unique_steps) < 3:
        return None
    return unique_steps[:3]


def generate_study_plan(
    database: Database,
    session_id: str,
    settings: Settings | None = None,
) -> StudyPlanResponse:
    """Generate or return a cached study plan for a completed session."""

    resolved_settings = settings or get_settings()
    session = get_session(database, session_id)
    if session is None:
        raise SessionError("Session not found.")
    if session.status != "completed":
        raise SessionError("Study plan is only available after session completion.")
    if session.study_plan is not None:
        return StudyPlanResponse.model_validate(session.study_plan.model_dump())

    performance_summary = _build_performance_summary(session_id, database)
    steps = _generate_openai_plan(performance_summary, resolved_settings)
    provider_used = "openai" if steps else "fallback"
    is_fallback = steps is None
    resolved_steps = steps or _fallback_steps(performance_summary)

    stored_plan = StoredStudyPlan(
        session_id=session_id,
        performance_summary=performance_summary,
        study_plan_steps=resolved_steps,
        provider_used=provider_used,
        is_fallback=is_fallback,
        generated_at=_utcnow(),
    )
    _sessions_collection(database).update_one(
        {"session_id": session_id},
        {"$set": {"study_plan": stored_plan.model_dump(mode="python"), "updated_at": _utcnow()}},
    )
    return StudyPlanResponse.model_validate(stored_plan.model_dump())
