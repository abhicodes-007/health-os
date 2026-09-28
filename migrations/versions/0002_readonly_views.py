"""Read-only approved-views + read-only role (plan 4.2).

The agent reads the DB through VIEWs filtered by review_status='approved' AND deleted_at
IS NULL, not through tables — otherwise sql_query would reach staging and the agent would
cite an unvalidated extraction as fact. A separate v_observations_pending — for the review
cycle (explicitly marked). Role health_readonly: statement_timeout=5s, SELECT only on views
(not on audit_log/staging).

Note (plan 2.1): no RLS until Phase 6; views without security_invoker run with the owner's
privileges — acceptable for single-user. In Phase 6 add security_invoker + RLS.
"""
from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE VIEW v_observations AS
        SELECT o.id, o.user_id, ot.code AS type_code, ot.name_uk, ot.category, ot.specimen,
               o.effective_at, o.value_type, o.value_numeric, o.comparator, o.value_text,
               o.unit, o.value_canonical, ot.canonical_unit, o.ref_min, o.ref_max, o.status,
               o.result_status, o.context, o.group_id, o.panel_id, o.notes
          FROM observations o
          JOIN observation_types ot ON ot.id = o.type_id
         WHERE o.review_status = 'approved' AND o.deleted_at IS NULL;

    CREATE VIEW v_observations_pending AS
        SELECT o.id, o.user_id, ot.code AS type_code, ot.name_uk,
               o.effective_at, o.value_numeric, o.unit, o.value_canonical, o.status,
               o.review_status, 'PENDING — unverified, do not cite as fact' AS review_note
          FROM observations o
          JOIN observation_types ot ON ot.id = o.type_id
         WHERE o.review_status <> 'approved' AND o.deleted_at IS NULL;

    CREATE VIEW v_medications_current AS
        SELECT id, user_id, medication_name, product_type, dose_amount, dose_unit, route,
               times_per_day, max_daily_mg, dosing_pattern, atc_code, start_date, prescribed_for
          FROM medications
         WHERE status = 'taking' AND deleted_at IS NULL;

    CREATE VIEW v_diagnoses AS
        SELECT id, user_id, diagnosed_at, diagnosis_name, icd10_code,
               clinical_status, verification_status, severity, notes
          FROM diagnoses
         WHERE deleted_at IS NULL;

    -- Allergies: including verified=false (fail-safe, plan 3.7)
    CREATE VIEW v_allergies AS
        SELECT id, user_id, allergen, allergen_type, reaction, severity, verified, notes
          FROM allergies
         WHERE deleted_at IS NULL;

    -- Read-only role (group). The MCP login role will inherit it in Phase 1.
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'health_readonly') THEN
            CREATE ROLE health_readonly NOLOGIN;
        END IF;
    END $$;
    ALTER ROLE health_readonly SET statement_timeout = '5s';
    GRANT USAGE ON SCHEMA public TO health_readonly;
    GRANT SELECT ON v_observations, v_observations_pending, v_medications_current,
                    v_diagnoses, v_allergies, health_timeline TO health_readonly;
    """
    )


def downgrade() -> None:
    op.execute(
        """
    REVOKE ALL ON v_observations, v_observations_pending, v_medications_current,
                  v_diagnoses, v_allergies, health_timeline FROM health_readonly;
    DROP VIEW IF EXISTS v_allergies;
    DROP VIEW IF EXISTS v_diagnoses;
    DROP VIEW IF EXISTS v_medications_current;
    DROP VIEW IF EXISTS v_observations_pending;
    DROP VIEW IF EXISTS v_observations;
    -- keep health_readonly (it may be shared); DROP ROLE manually if needed
    """
    )


