"""Question seeding service."""

from collections.abc import Sequence

from pymongo.collection import Collection
from pymongo.database import Database

from app.models.schemas import QuestionRecord, SeedQuestionsResponse
from app.scripts.seed_data import SEED_QUESTIONS


def seed_questions(database: Database, questions: Sequence[dict] | None = None) -> SeedQuestionsResponse:
    """Upsert static questions into MongoDB using stable question IDs."""

    payload = questions or SEED_QUESTIONS
    collection: Collection = database["questions"]
    inserted_count = 0
    updated_count = 0

    for question in payload:
        validated = QuestionRecord.model_validate(question)
        existing = collection.find_one({"question_id": validated.question_id}, {"_id": 1})
        collection.update_one(
            {"question_id": validated.question_id},
            {"$set": validated.model_dump(mode="python")},
            upsert=True,
        )
        if existing:
            updated_count += 1
        else:
            inserted_count += 1

    total_questions = collection.count_documents({})
    return SeedQuestionsResponse(
        inserted_count=inserted_count,
        updated_count=updated_count,
        total_questions=total_questions,
    )
