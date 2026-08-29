"""Persistence-level enumerations."""

from enum import StrEnum


class JobStatus(StrEnum):
    """Application status values from the project plan."""

    PENDING_ANALYSIS = "pending_analysis"
    PREPARING = "preparing"
    APPLIED = "applied"
    CONTACTED = "contacted"
    INTERVIEW = "interview"
    CLOSED = "closed"


class DocumentStatus(StrEnum):
    """Indexing lifecycle across SQLite and the vector store."""

    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
