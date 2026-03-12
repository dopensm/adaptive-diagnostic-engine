"""Tests for pure adaptive engine behavior."""

from app.config import Settings
from app.models.schemas import QuestionOption, QuestionRecord, SessionResponseRecord
from app.services.adaptive_engine import build_session_summary, select_next_question, update_ability_score


def make_question(question_id: str, topic: str, difficulty: float) -> QuestionRecord:
    return QuestionRecord(
        question_id=question_id,
        prompt=f"Prompt for {question_id}",
        topic=topic,
        tags=[topic.lower()],
        difficulty=difficulty,
        choices=[
            QuestionOption(key="A", text="Option A"),
            QuestionOption(key="B", text="Option B"),
        ],
        correct_answer="A",
    )


def test_correct_answer_raises_ability() -> None:
    settings = Settings()
    updated = update_ability_score(0.5, 0.5, True, settings)
    assert updated > 0.5


def test_incorrect_answer_lowers_ability() -> None:
    settings = Settings()
    updated = update_ability_score(0.5, 0.5, False, settings)
    assert updated < 0.5


def test_ability_is_clamped_to_bounds() -> None:
    settings = Settings(ability_step_scale=1.0, ability_floor=0.1, ability_ceiling=1.0)
    assert update_ability_score(0.99, 0.1, True, settings) <= 1.0
    assert update_ability_score(0.11, 1.0, False, settings) >= 0.1


def test_next_question_prefers_closest_difficulty_and_avoids_repeats() -> None:
    questions = [
        make_question("q1", "Algebra", 0.2),
        make_question("q2", "Geometry", 0.48),
        make_question("q3", "Vocabulary", 0.8),
    ]
    next_question = select_next_question(questions, ["q1"], 0.5)
    assert next_question is not None
    assert next_question.question_id == "q2"


def test_next_question_uses_topic_balance_as_tiebreaker() -> None:
    questions = [
        make_question("q1", "Algebra", 0.45),
        make_question("q2", "Algebra", 0.5),
        make_question("q3", "Geometry", 0.5),
    ]
    next_question = select_next_question(questions, ["q1"], 0.5)
    assert next_question is not None
    assert next_question.question_id == "q3"


def test_build_session_summary_aggregates_topic_weaknesses() -> None:
    responses = [
        SessionResponseRecord(
            question_id="q1",
            selected_answer="A",
            correct_answer="A",
            is_correct=True,
            difficulty=0.3,
            topic="Algebra",
            ability_before=0.5,
            ability_after=0.6,
            answered_at="2026-03-12T12:00:00Z",
        ),
        SessionResponseRecord(
            question_id="q2",
            selected_answer="A",
            correct_answer="B",
            is_correct=False,
            difficulty=0.6,
            topic="Geometry",
            ability_before=0.6,
            ability_after=0.45,
            answered_at="2026-03-12T12:01:00Z",
        ),
    ]
    session_summary, performance_summary = build_session_summary(responses, 0.45, "session-1")
    assert session_summary.correct_answers == 1
    assert session_summary.incorrect_answers == 1
    assert session_summary.highest_difficulty_reached == 0.6
    assert session_summary.weakest_topics == ["Geometry"]
    assert performance_summary.session_id == "session-1"
