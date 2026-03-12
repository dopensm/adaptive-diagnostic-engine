"""CLI entrypoint for seeding questions."""

from app.db.mongo import get_database
from app.services.seeding import seed_questions


def main() -> None:
    """Seed the question bank and print a short summary."""

    result = seed_questions(get_database())
    print(
        "Seed complete:",
        f"inserted={result.inserted_count}",
        f"updated={result.updated_count}",
        f"total={result.total_questions}",
    )


if __name__ == "__main__":
    main()
