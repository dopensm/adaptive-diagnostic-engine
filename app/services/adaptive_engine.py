"""Pure adaptive testing logic."""

from collections import defaultdict
from math import exp

from app.config import Settings, get_settings
from app.models.schemas import (
    PerformanceSummary,
    QuestionPublic,
    QuestionRecord,
    SessionResponseRecord,
    SessionSummary,
    TopicPerformance,
)


def clamp_ability(value: float, settings: Settings | None = None) -> float:
    """Clamp an ability score to configured bounds."""

    resolved_settings = settings or get_settings()
    return max(resolved_settings.ability_floor, min(resolved_settings.ability_ceiling, value))


def update_ability_score(
    current_ability: float,
    question_difficulty: float,
    is_correct: bool,
    settings: Settings | None = None,
) -> float:
    """Update ability using a simple 1D IRT-inspired adjustment rule.

    The expected probability is modeled with a logistic curve over
    `current_ability - question_difficulty`. The next score moves in the
    direction of `(observed - expected)` scaled by a configurable step size.
    """

    resolved_settings = settings or get_settings()
    expected_correct = 1.0 / (1.0 + exp(-(current_ability - question_difficulty) * 6.0))
    observed = 1.0 if is_correct else 0.0
    adjustment = resolved_settings.ability_step_scale * (observed - expected_correct)
    return clamp_ability(current_ability + adjustment, resolved_settings)


def to_public_question(question: QuestionRecord) -> QuestionPublic:
    """Strip answer-key fields from a stored question."""

    return QuestionPublic.model_validate(question.model_dump(exclude={"correct_answer"}))


def select_next_question(
    questions: list[QuestionRecord],
    asked_question_ids: list[str],
    target_ability: float,
) -> QuestionRecord | None:
    """Pick the best next unanswered question.

    Selection prioritizes questions closest to the target ability and applies
    a light topic-balancing preference to avoid repeatedly choosing one topic.
    """

    remaining = [question for question in questions if question.question_id not in set(asked_question_ids)]
    if not remaining:
        return None

    topic_counts: dict[str, int] = defaultdict(int)
    asked_lookup = {question.question_id: question for question in questions}
    for question_id in asked_question_ids:
        question = asked_lookup.get(question_id)
        if question:
            topic_counts[question.topic] += 1

    return min(
        remaining,
        key=lambda question: (
            abs(question.difficulty - target_ability),
            topic_counts[question.topic],
            question.question_id,
        ),
    )


def build_session_summary(
    responses: list[SessionResponseRecord],
    ability_score: float,
    session_id: str,
) -> tuple[SessionSummary, PerformanceSummary]:
    """Build aggregate session and performance summaries from responses."""

    total_questions = len(responses)
    correct_answers = sum(1 for response in responses if response.is_correct)
    incorrect_answers = total_questions - correct_answers
    accuracy = correct_answers / total_questions if total_questions else 0.0
    highest_difficulty_reached = max(
        (response.difficulty for response in responses),
        default=get_settings().baseline_ability,
    )

    topic_buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "incorrect": 0})
    for response in responses:
        bucket = topic_buckets[response.topic]
        if response.is_correct:
            bucket["correct"] += 1
        else:
            bucket["incorrect"] += 1

    topic_breakdown = [
        TopicPerformance(topic=topic, correct=stats["correct"], incorrect=stats["incorrect"])
        for topic, stats in sorted(topic_buckets.items())
    ]
    weakest_topics = [
        topic_result.topic
        for topic_result in sorted(
            topic_breakdown,
            key=lambda result: (-result.incorrect, result.correct, result.topic),
        )
        if topic_result.incorrect > 0
    ][:3]

    session_summary = SessionSummary(
        total_questions=total_questions,
        correct_answers=correct_answers,
        incorrect_answers=incorrect_answers,
        accuracy=accuracy,
        highest_difficulty_reached=highest_difficulty_reached,
        weakest_topics=weakest_topics,
        topic_breakdown=topic_breakdown,
    )
    performance_summary = PerformanceSummary(
        session_id=session_id,
        ability_score=ability_score,
        total_questions=total_questions,
        correct_answers=correct_answers,
        incorrect_answers=incorrect_answers,
        highest_difficulty_reached=highest_difficulty_reached,
        weakest_topics=weakest_topics,
        topic_breakdown=topic_breakdown,
    )
    return session_summary, performance_summary
