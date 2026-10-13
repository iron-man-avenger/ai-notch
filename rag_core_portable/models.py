# ==============================================================================
# 1. DATABASE SCHEMA (models.py)
# Supports both PostgreSQL with pgvector extension AND local SQLite Vector store.
# ==============================================================================

from datetime import datetime
from typing import Optional

# ── A. PostgreSQL + pgvector Model (Using SQLAlchemy) ─────────────────────────
try:
    from sqlalchemy import Integer, String, Text, DateTime
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    from pgvector.sqlalchemy import Vector

    class Base(DeclarativeBase):
        pass

    class DocumentChunkPG(Base):
        """
        PostgreSQL table with pgvector extension.
        Requires: CREATE EXTENSION IF NOT EXISTS vector; in PostgreSQL.
        """
        __tablename__ = "document_chunks"

        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        doc_ref: Mapped[str] = mapped_column(String(60), index=True)
        title: Mapped[str] = mapped_column(String(240))
        heading: Mapped[str] = mapped_column(String(240), default="")
        content: Mapped[str] = mapped_column(Text)
        
        # 384-dim vector for open-source BAAI/bge-small-en-v1.5 (or 1536 for OpenAI)
        embedding = mapped_column(Vector(384), nullable=True)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

except ImportError:
    pass

# ── B. Zero-Config SQLite Table Definition ────────────────────────────────────
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_ref TEXT NOT NULL,
    title TEXT NOT NULL,
    heading TEXT DEFAULT '',
    content TEXT NOT NULL,
    embedding TEXT, -- JSON array of floats or BLOB
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_ref ON document_chunks(doc_ref);
"""
