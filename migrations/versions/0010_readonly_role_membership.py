"""Let the app user switch to health_readonly (2026-09-29).

sql_query now always runs under `SET LOCAL ROLE health_readonly`, so arbitrary SELECTs see only
the approved views even when READONLY_DATABASE_URL is not configured. SET ROLE needs membership;
a superuser has it implicitly, a regular owner gets it here.
"""
from __future__ import annotations

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user)
           AND NOT pg_has_role(current_user, 'health_readonly', 'MEMBER') THEN
            EXECUTE format('GRANT health_readonly TO %I', current_user);
        END IF;
    END $$;
    """
    )


def downgrade() -> None:
    op.execute(
        """
    DO $$
    BEGIN
        IF NOT (SELECT rolsuper FROM pg_roles WHERE rolname = current_user) THEN
            EXECUTE format('REVOKE health_readonly FROM %I', current_user);
        END IF;
    END $$;
    """
    )
