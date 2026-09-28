"""Hardening the read-only role: SELECT only on approved-views, nothing more (plan 4.2).

health_readonly has NO access to base tables, audit_log, ingestion_sources (raw
payloads), critical_thresholds, etc. — even if sql_query tries to read them, the DB
refuses at the privilege level. Access only via v_* (which run with the owner's privileges
and filter approved themselves). LOGIN + password is enabled by a separate setup script
from .env (not in git).
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_VIEWS = ["v_observations", "v_observations_pending", "v_medications_current",
          "v_diagnoses", "v_allergies", "health_timeline"]


def upgrade() -> None:
    # Remove any inherited/default privileges, leave only SELECT on views.
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'health_readonly') THEN
            CREATE ROLE health_readonly NOLOGIN;
        END IF;
    END $$;

    -- revoke everything unnecessary
    REVOKE ALL ON ALL TABLES IN SCHEMA public FROM health_readonly;
    REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM health_readonly;
    REVOKE ALL ON SCHEMA public FROM health_readonly;

    -- leave exactly what's necessary
    GRANT USAGE ON SCHEMA public TO health_readonly;
    -- users — a stub (UUID only), needed by read tools to resolve user_id; not PHI
    GRANT SELECT ON users TO health_readonly;
    ALTER ROLE health_readonly SET statement_timeout = '5s';
    ALTER ROLE health_readonly SET default_transaction_read_only = on;
    """
        + "".join(f"GRANT SELECT ON {v} TO health_readonly;\n" for v in _VIEWS)
    )


def downgrade() -> None:
    op.execute(
        "ALTER ROLE health_readonly RESET default_transaction_read_only;"
    )
