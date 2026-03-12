"""In-memory test doubles for Mongo-style access."""

from __future__ import annotations

from copy import deepcopy


class FakeUpdateResult:
    """Minimal update result used by tests."""

    def __init__(self, matched_count: int) -> None:
        self.matched_count = matched_count


class FakeCollection:
    """Small subset of a Mongo collection interface."""

    def __init__(self) -> None:
        self.documents: list[dict] = []

    def find(self, query: dict | None = None, projection: dict | None = None) -> list[dict]:
        return [self._project(document, projection) for document in self.documents if self._matches(document, query or {})]

    def find_one(self, query: dict, projection: dict | None = None) -> dict | None:
        for document in self.documents:
            if self._matches(document, query):
                return self._project(document, projection)
        return None

    def insert_one(self, document: dict) -> None:
        self.documents.append(deepcopy(document))

    def update_one(self, query: dict, update: dict, upsert: bool = False) -> FakeUpdateResult:
        for index, document in enumerate(self.documents):
            if self._matches(document, query):
                updated = deepcopy(document)
                if "$set" in update:
                    updated.update(deepcopy(update["$set"]))
                self.documents[index] = updated
                return FakeUpdateResult(matched_count=1)

        if upsert:
            new_document = deepcopy(query)
            if "$set" in update:
                new_document.update(deepcopy(update["$set"]))
            self.documents.append(new_document)
            return FakeUpdateResult(matched_count=0)

        return FakeUpdateResult(matched_count=0)

    def count_documents(self, query: dict | None = None) -> int:
        return len([document for document in self.documents if self._matches(document, query or {})])

    @staticmethod
    def _matches(document: dict, query: dict) -> bool:
        return all(document.get(key) == value for key, value in query.items())

    @staticmethod
    def _project(document: dict, projection: dict | None) -> dict:
        copied = deepcopy(document)
        if not projection:
            return copied
        if projection.get("_id") == 0:
            copied.pop("_id", None)
        return copied


class FakeDatabase:
    """Dictionary-backed fake database."""

    def __init__(self) -> None:
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]
