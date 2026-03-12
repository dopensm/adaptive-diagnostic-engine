"""MongoDB client helpers."""

from functools import lru_cache

from fastapi import HTTPException, status
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.database import Database

from app.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_mongo_client() -> MongoClient:
    """Return a cached Mongo client."""

    settings = get_settings()
    return MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)


def get_database(settings: Settings | None = None) -> Database:
    """Return the configured Mongo database."""

    resolved_settings = settings or get_settings()
    return get_mongo_client()[resolved_settings.mongo_database]


def get_db() -> Database:
    """FastAPI dependency for Mongo database access."""

    database = get_database()
    try:
        database.command("ping")
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is unavailable. Check MONGO_URI and ensure the database is running.",
        ) from exc
    return database
