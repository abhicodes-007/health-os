"""Phase 3 — embedding vector column on document_chunks (2026-07-16).

Model: intfloat/multilingual-e5-base (768-dim, local, uk/ru/en). Embeddings are
normalized → cosine distance. HNSW index for ANN search. Switching to a model with a
different dimension = a new column-type migration + recomputation (for a small corpus —
instant).

The full-text tsvector (0005) stays — search becomes HYBRID (keyword + vector).
"""
from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

EMBED_DIM = 768


def upgrade() -> None:
    op.execute(
        f"""
    ALTER TABLE document_chunks ADD COLUMN embedding vector({EMBED_DIM});
    ALTER TABLE document_chunks ADD COLUMN embedding_model VARCHAR(80);
    -- HNSW for cosine similarity (embeddings are normalized)
    CREATE INDEX idx_chunks_embedding ON document_chunks
        USING hnsw (embedding vector_cosine_ops);
        """
    )


def downgrade() -> None:
    op.execute(
        """
    DROP INDEX IF EXISTS idx_chunks_embedding;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_model;
        """
    )
