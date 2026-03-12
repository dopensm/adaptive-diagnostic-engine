"""Administrative API routes."""

from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.db.mongo import get_db
from app.models.schemas import SeedQuestionsResponse
from app.services.seeding import seed_questions

router = APIRouter()


@router.post("/seed", response_model=SeedQuestionsResponse)
def seed_question_bank(database: Database = Depends(get_db)) -> SeedQuestionsResponse:
    """Seed the static question bank into MongoDB."""

    return seed_questions(database)
