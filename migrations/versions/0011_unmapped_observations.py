"""Keep unmapped lab rows instead of dropping them (#12, 2026-10-03).

A row whose printed name isn't in the catalog (or whose unit can't belong to the matched type)
used to be returned with a note and then lost. Now it is stored as a pending observation with
type_id NULL and the printed name in raw_name, so it shows up in v_observations_pending and the
health summary until map_pending_observation assigns a type. An unmapped row can never be
approved (chk_unmapped_not_approved), so v_observations keeps its inner join.
"""
from __future__ import annotations

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    ALTER TABLE observations ALTER COLUMN type_id DROP NOT NULL;
    ALTER TABLE observations ADD COLUMN raw_name VARCHAR(300);
    ALTER TABLE observations ADD CONSTRAINT chk_unmapped_not_approved
        CHECK (type_id IS NOT NULL OR review_status <> 'approved');

    -- left join: unmapped rows are listed with their printed name (columns only appended)
    CREATE OR REPLACE VIEW v_observations_pending AS
        SELECT o.id, o.user_id, ot.code AS type_code, ot.name_uk,
               o.effective_at, o.value_numeric, o.unit, o.value_canonical, o.status,
               o.review_status, 'PENDING — unverified, do not cite as fact' AS review_note,
               o.raw_name, o.value_text, o.ref_min, o.ref_max, o.source_id,
               (o.type_id IS NULL) AS unmapped
          FROM observations o
          LEFT JOIN observation_types ot ON ot.id = o.type_id
         WHERE o.review_status <> 'approved' AND o.deleted_at IS NULL;
    GRANT SELECT ON v_observations_pending TO health_readonly;
    """
    )


def downgrade() -> None:
    op.execute(
        """
    DROP VIEW v_observations_pending;
    CREATE VIEW v_observations_pending AS
        SELECT o.id, o.user_id, ot.code AS type_code, ot.name_uk,
               o.effective_at, o.value_numeric, o.unit, o.value_canonical, o.status,
               o.review_status, 'PENDING — unverified, do not cite as fact' AS review_note
          FROM observations o
          JOIN observation_types ot ON ot.id = o.type_id
         WHERE o.review_status <> 'approved' AND o.deleted_at IS NULL;
    GRANT SELECT ON v_observations_pending TO health_readonly;
    -- the old schema has no place for unmapped rows
    DELETE FROM observation_history WHERE observation_id IN
        (SELECT id FROM observations WHERE type_id IS NULL);
    DELETE FROM observations WHERE type_id IS NULL;
    ALTER TABLE observations DROP CONSTRAINT chk_unmapped_not_approved;
    ALTER TABLE observations DROP COLUMN raw_name;
    ALTER TABLE observations ALTER COLUMN type_id SET NOT NULL;
    """
    )
