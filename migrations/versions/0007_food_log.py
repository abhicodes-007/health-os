"""Food log — food_log table + approved view (2026-09-20).

A separate food-diary entity: free-text meal description + optional nutrients
(calories/macros). NOT observations (no unit gate, no critical values) — the user's own
low-risk data, auto-approved like diagnoses/medications.

Reading — via v_food_log (deleted_at IS NULL); the readonly role has access only to the
view, not the raw table. Here we also IDEMPOTENTLY re-grant on the 6 existing views — so
that the live manual grant fix (grants that were lost after 0004–0006) becomes baked into
code and survives a future recreation of the views.
"""
from __future__ import annotations

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_EXISTING_VIEWS = ["v_observations", "v_observations_pending", "v_medications_current",
                   "v_diagnoses", "v_allergies", "health_timeline"]


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE food_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id       UUID NOT NULL REFERENCES users(id),
        eaten_at      TIMESTAMPTZ NOT NULL,             -- date+time of the meal
        meal_type     VARCHAR(20),                       -- breakfast/lunch/dinner/snack/drink
        description   TEXT NOT NULL,                      -- free-text meal description
        portion       VARCHAR(80),                        -- "200 g", "1 plate"
        calories_kcal NUMERIC,                            -- optional nutrients (model estimate)
        protein_g     NUMERIC,
        carbs_g       NUMERIC,
        fat_g         NUMERIC,
        fiber_g       NUMERIC,
        notes         TEXT,
        source_id     UUID REFERENCES ingestion_sources(id),
        deleted_at    TIMESTAMPTZ,
        created_at    TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_food_log_user ON food_log (user_id, eaten_at DESC);

    CREATE VIEW v_food_log AS
        SELECT id, user_id, eaten_at, meal_type, description, portion,
               calories_kcal, protein_g, carbs_g, fat_g, fiber_g, notes
          FROM food_log
         WHERE deleted_at IS NULL;

    GRANT SELECT ON v_food_log TO health_readonly;
    """
        # idempotent re-grant on existing views (durable bug fix)
        + "".join(f"GRANT SELECT ON {v} TO health_readonly;\n" for v in _EXISTING_VIEWS)
    )


def downgrade() -> None:
    op.execute(
        """
    REVOKE ALL ON v_food_log FROM health_readonly;
    DROP VIEW IF EXISTS v_food_log;
    DROP TABLE IF EXISTS food_log;
    """
    )
