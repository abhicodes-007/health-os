"""Phase 2/3 tables: qualitative_values, device_alerts, document_chunks, pgvector.

- qualitative_values + synonyms (plan 3.11): 'не виявлено'/'neg'/'негат.' → canonical + ordinal.
- device_alerts (plan 3.9 v3): "possible fibrillation rhythm"/SpO₂-alert/fall — event flags,
  NOT numeric samples; they feed red-flag logic, not drown in daily aggregates.
- document_chunks: text chunks for semantic search. The embedding column is added by a SEPARATE
  migration AFTER the model is chosen (plan: don't fix vector(N) now).
- pgvector extension is enabled here (Phase 3), the image already has it.
"""
from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE qualitative_values (
        id SERIAL PRIMARY KEY,
        canonical    VARCHAR(40) NOT NULL UNIQUE,   -- negative/trace/weakly_positive/positive/...
        ordinal_rank INT                            -- for trends of qualitative results
    );
    CREATE TABLE qualitative_synonyms (
        id SERIAL PRIMARY KEY,
        value_id INT NOT NULL REFERENCES qualitative_values(id),
        synonym  VARCHAR(80) NOT NULL,
        lang     VARCHAR(5)
    );
    CREATE UNIQUE INDEX uq_qual_syn ON qualitative_synonyms (lower(synonym));

    CREATE TABLE device_alerts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id     UUID NOT NULL REFERENCES users(id),
        alert_type  VARCHAR(40) NOT NULL,           -- afib/irregular_rhythm/low_spo2/fall/high_hr
        detected_at TIMESTAMPTZ NOT NULL,
        source      VARCHAR(60),                     -- apple_watch...
        reliability VARCHAR(20),                     -- consumer_grade / medical
        raw         JSONB,
        reviewed    BOOLEAN DEFAULT FALSE,
        created_at  TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX idx_device_alerts_user ON device_alerts (user_id, detected_at DESC);

    CREATE TABLE document_chunks (
        id          BIGSERIAL PRIMARY KEY,
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INT NOT NULL,
        content     TEXT NOT NULL
        -- embedding vector(N): a SEPARATE migration after the model is chosen (plan 3.4)
    );
    CREATE INDEX idx_chunks_doc ON document_chunks (document_id);
    """
    )


def downgrade() -> None:
    op.execute(
        """
    DROP TABLE IF EXISTS document_chunks;
    DROP TABLE IF EXISTS device_alerts;
    DROP TABLE IF EXISTS qualitative_synonyms;
    DROP TABLE IF EXISTS qualitative_values;
    -- keep the vector extension
    """
    )
