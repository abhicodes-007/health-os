"""Templates for frequent meals — quick entry in one call (2026-09-20).

meal_templates: a saved meal profile (nutrients JSONB + gi). log_from_template
multiplies by portion_factor and writes to food_log/food_nutrients via the existing
add_food_log. View + readonly grant in the migration (lesson from 0007).
"""
from __future__ import annotations

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_EXISTING_VIEWS = ["v_observations", "v_observations_pending", "v_medications_current",
                   "v_diagnoses", "v_allergies", "v_food_log", "v_food_nutrients",
                   "health_timeline"]


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE meal_templates (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id        UUID NOT NULL REFERENCES users(id),
        name           VARCHAR(80) NOT NULL,
        meal_type      VARCHAR(20),
        description    TEXT,
        nutrients      JSONB,               -- {code: amount_per_1_portion}
        glycemic_index SMALLINT,
        created_at     TIMESTAMPTZ DEFAULT NOW(),
        deleted_at     TIMESTAMPTZ
    );
    CREATE UNIQUE INDEX uq_meal_template_name
        ON meal_templates (user_id, lower(name)) WHERE deleted_at IS NULL;

    CREATE VIEW v_meal_templates AS
        SELECT id, user_id, name, meal_type, description, nutrients, glycemic_index
          FROM meal_templates
         WHERE deleted_at IS NULL;

    GRANT SELECT ON v_meal_templates TO health_readonly;
    """
        + "".join(f"GRANT SELECT ON {v} TO health_readonly;\n" for v in _EXISTING_VIEWS)
    )


def downgrade() -> None:
    op.execute(
        """
    DROP VIEW IF EXISTS v_meal_templates;
    DROP TABLE IF EXISTS meal_templates;
    """
    )
