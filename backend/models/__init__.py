# backend/models/__init__.py

from .database import (
    Base,
    Document,
    DocumentChunk,
    DocumentMeta,  # ✅ Renommé
    Project,
    Session,
    IngestionLog,
    init_db
)

__all__ = [
    "Base",
    "Document",
    "DocumentChunk",
    "DocumentMeta",  # ✅ Renommé
    "Project",
    "Session",
    "IngestionLog",
    "init_db"
]