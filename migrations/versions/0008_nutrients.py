"""Full nutrient tracking for food (2026-09-20).

Moving food_log to a canonical model: instead of 5 fixed macro columns — a
nutrient_types reference (~40 nutrients with daily rda + safe upper_limit) +
food_nutrients rows (nutrient per meal), mirroring observation_types/observations.
Source-agnostic (food_log.nutrient_source = model_estimate/usda) — ready for a future
import of USDA FoodData Central.

Plus on food_log: glycemic_index/glycemic_load, symptoms/wellbeing (reaction after eating).
Grants on the new views — right here (lesson from 0007: grants are baked into the migration).
"""
from __future__ import annotations

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_EXISTING_VIEWS = ["v_observations", "v_observations_pending", "v_medications_current",
                   "v_diagnoses", "v_allergies", "health_timeline"]


def upgrade() -> None:
    op.execute(
        """
    -- food_log: canonical nutrient model + glycemic + reaction
    DROP VIEW IF EXISTS v_food_log;
    ALTER TABLE food_log
        DROP COLUMN calories_kcal,
        DROP COLUMN protein_g,
        DROP COLUMN carbs_g,
        DROP COLUMN fat_g,
        DROP COLUMN fiber_g,
        ADD COLUMN nutrient_source VARCHAR(20) DEFAULT 'model_estimate',
        ADD COLUMN glycemic_index  SMALLINT,
        ADD COLUMN glycemic_load   NUMERIC,
        ADD COLUMN symptoms        TEXT,
        ADD COLUMN wellbeing       VARCHAR(20);

    -- nutrient reference
    CREATE TABLE nutrient_types (
        id SERIAL PRIMARY KEY,
        code        VARCHAR(40) NOT NULL UNIQUE,
        name_uk     VARCHAR(80) NOT NULL,
        name_en     VARCHAR(80),
        unit        VARCHAR(10) NOT NULL,          -- kcal/g/mg/mcg/ml
        category    VARCHAR(20) NOT NULL,          -- energy/macro/fat/mineral/vitamin/other
        rda         NUMERIC,                        -- daily norm (adult male 19-50)
        upper_limit NUMERIC,                        -- safe upper limit (where it exists)
        sort_order  INT
    );

    -- nutrients per meal
    CREATE TABLE food_nutrients (
        id BIGSERIAL PRIMARY KEY,
        food_log_id UUID NOT NULL REFERENCES food_log(id) ON DELETE CASCADE,
        nutrient_id INT  NOT NULL REFERENCES nutrient_types(id),
        amount      NUMERIC NOT NULL,
        UNIQUE (food_log_id, nutrient_id)
    );
    CREATE INDEX idx_food_nutrients_nutrient ON food_nutrients (nutrient_id);

    -- approved views
    CREATE VIEW v_food_log AS
        SELECT id, user_id, eaten_at, meal_type, description, portion,
               nutrient_source, glycemic_index, glycemic_load, symptoms, wellbeing, notes
          FROM food_log
         WHERE deleted_at IS NULL;

    CREATE VIEW v_food_nutrients AS
        SELECT fn.food_log_id, f.user_id, f.eaten_at, f.meal_type,
               nt.code AS nutrient_code, nt.name_uk, nt.category, nt.unit,
               fn.amount, nt.rda, nt.upper_limit
          FROM food_nutrients fn
          JOIN food_log f       ON f.id = fn.food_log_id AND f.deleted_at IS NULL
          JOIN nutrient_types nt ON nt.id = fn.nutrient_id;

    GRANT SELECT ON v_food_log TO health_readonly;
    GRANT SELECT ON v_food_nutrients TO health_readonly;
    """
        + "".join(f"GRANT SELECT ON {v} TO health_readonly;\n" for v in _EXISTING_VIEWS)
    )


def downgrade() -> None:
    op.execute(
        """
    DROP VIEW IF EXISTS v_food_nutrients;
    DROP VIEW IF EXISTS v_food_log;
    DROP TABLE IF EXISTS food_nutrients;
    DROP TABLE IF EXISTS nutrient_types;
    ALTER TABLE food_log
        DROP COLUMN nutrient_source,
        DROP COLUMN glycemic_index,
        DROP COLUMN glycemic_load,
        DROP COLUMN symptoms,
        DROP COLUMN wellbeing,
        ADD COLUMN calories_kcal NUMERIC,
        ADD COLUMN protein_g NUMERIC,
        ADD COLUMN carbs_g NUMERIC,
        ADD COLUMN fat_g NUMERIC,
        ADD COLUMN fiber_g NUMERIC;

    CREATE VIEW v_food_log AS
        SELECT id, user_id, eaten_at, meal_type, description, portion,
               calories_kcal, protein_g, carbs_g, fat_g, fiber_g, notes
          FROM food_log WHERE deleted_at IS NULL;
    GRANT SELECT ON v_food_log TO health_readonly;
    """
    )
