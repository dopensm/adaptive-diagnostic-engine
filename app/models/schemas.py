"""Pydantic schemas for questions, sessions, and study plans."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SessionStatus = Literal["in_progress", "completed"]


class QuestionOption(BaseModel):
    """A single answer option for a question."""

    key: str = Field(min_length=1, max_length=5)
    text: str = Field(min_length=1)


class QuestionBase(BaseModel):
    """Base fields shared by question models."""

    question_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    difficulty: float = Field(ge=0.1, le=1.0)
    choices: list[QuestionOption] = Field(min_length=2)
    explanation: str | None = None


class QuestionRecord(QuestionBase):
    """Stored question model including the correct answer."""

    correct_answer: str = Field(min_length=1, max_length=5)


class QuestionPublic(QuestionBase):
    """Question model returned to quiz clients."""


class TopicPerformance(BaseModel):
    """Performance summary for a topic."""

    topic: str
    correct: int = Field(ge=0)
    incorrect: int = Field(ge=0)


class SessionResponseRecord(BaseModel):
    """A single answered question within a session."""

    question_id: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    difficulty: float = Field(ge=0.1, le=1.0)
    topic: str
    ability_before: float = Field(ge=0.1, le=1.0)
    ability_after: float = Field(ge=0.1, le=1.0)
    answered_at: datetime


class SessionSummary(BaseModel):
    """Aggregate session results."""

    total_questions: int = Field(ge=0)
    correct_answers: int = Field(ge=0)
    incorrect_answers: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    highest_difficulty_reached: float = Field(ge=0.1, le=1.0)
    weakest_topics: list[str] = Field(default_factory=list)
    topic_breakdown: list[TopicPerformance] = Field(default_factory=list)


class UserSession(BaseModel):
    """Stored session state."""

    session_id: str
    status: SessionStatus
    ability_score: float = Field(ge=0.1, le=1.0)
    asked_question_ids: list[str] = Field(default_factory=list)
    responses: list[SessionResponseRecord] = Field(default_factory=list)
    question_limit: int = Field(ge=1)
    summary: SessionSummary | None = None
    study_plan: "StoredStudyPlan | None" = None
    created_at: datetime
    updated_at: datetime


class StartSessionResponse(BaseModel):
    """Response for starting a new session."""

    session_id: str
    ability_score: float = Field(ge=0.1, le=1.0)
    question: QuestionPublic
    remaining_questions: int = Field(ge=0)


class SubmitAnswerRequest(BaseModel):
    """Payload for submitting an answer."""

    question_id: str = Field(min_length=1)
    selected_answer: str = Field(min_length=1, max_length=5)


class SubmitAnswerResponse(BaseModel):
    """Response after submitting an answer."""

    is_correct: bool
    ability_score: float = Field(ge=0.1, le=1.0)
    session_status: SessionStatus
    remaining_questions: int = Field(ge=0)
    next_question: QuestionPublic | None = None
    summary: SessionSummary | None = None


class PerformanceSummary(BaseModel):
    """Compact data sent to study-plan generation."""

    session_id: str
    ability_score: float = Field(ge=0.1, le=1.0)
    total_questions: int = Field(ge=0)
    correct_answers: int = Field(ge=0)
    incorrect_answers: int = Field(ge=0)
    highest_difficulty_reached: float = Field(ge=0.1, le=1.0)
    weakest_topics: list[str] = Field(default_factory=list)
    topic_breakdown: list[TopicPerformance] = Field(default_factory=list)


class StudyPlanResponse(BaseModel):
    """Returned study plan and supporting metadata."""

    session_id: str
    performance_summary: PerformanceSummary
    study_plan_steps: list[str] = Field(min_length=3, max_length=3)
    provider_used: str
    is_fallback: bool


class StoredStudyPlan(StudyPlanResponse):
    """Cached study plan stored with a session."""

    generated_at: datetime


class SeedQuestionsResponse(BaseModel):
    """Response for seed operations."""

    inserted_count: int = Field(ge=0)
    updated_count: int = Field(ge=0)
    total_questions: int = Field(ge=0)
