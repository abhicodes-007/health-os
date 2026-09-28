"""Enables LOGIN + password for the health_readonly role from .env (idempotent).

The password lives only in .env (outside git). Run:  uv run python -m scripts.setup_readonly
After this, MCP reads go through a separate restricted role (SELECT only on approved-views).
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from core.config import settings
from core.db import engine


def main() -> int:
    pw = settings.readonly_db_password
    if not pw:
        print("READONLY_DB_PASSWORD not set in .env — skipping (the read-only role stays NOLOGIN).")
        return 1
    with engine.begin() as conn:
        # ALTER ROLE doesn't accept a placeholder parameter for the password → format the literal safely
        pw_literal = "'" + pw.replace("'", "''") + "'"
        conn.execute(text(f"ALTER ROLE health_readonly WITH LOGIN PASSWORD {pw_literal}"))
    print("OK: health_readonly is now LOGIN. MCP reads can connect with the restricted role.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
