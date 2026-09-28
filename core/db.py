"""SQLAlchemy engine/session. ORM models are added in Phase 1."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Read-only engine for MCP reads (role health_readonly). Falls back to the main engine
# if the readonly role is not configured (dev/tests) — then protection stays at the code
# level (read-only tx in sql_query), but not at the DB privilege level.
readonly_engine = (
    create_engine(settings.readonly_database_url, pool_pre_ping=True, future=True)
    if settings.readonly_database_url
    else engine
)


class Base(DeclarativeBase):
    pass
