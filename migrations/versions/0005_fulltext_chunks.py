"""Phase 3 (lean version, 2026-07-16): full-text search over document_chunks WITHOUT embeddings.

Decision: while we work only through Claude Code (no API key and no local embedding
model), the agent itself does the "semantics" on top of a Postgres keyword index.
The vector column (`embedding vector(N)`) is added by a SEPARATE migration later, once a
local embedding model is chosen — the `search` tool interface won't change.

The `simple` config: no stemming (Postgres has no 'ukrainian'; 'russian' would distort
Ukrainian/English tokens). simple = tokenization + lowercase + accent-independent,
universal for mixed uk/ru/en medical text.
"""
from __future__ import annotations

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    -- FTS over chunks: generated tsvector column + GIN index
    ALTER TABLE document_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED;
    CREATE INDEX idx_chunks_fts ON document_chunks USING GIN (content_tsv);

    -- FTS over the full document text (for fallback search across a whole document)
    ALTER TABLE documents
        ADD COLUMN extracted_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(extracted_text, ''))) STORED;
    CREATE INDEX idx_documents_fts ON documents USING GIN (extracted_tsv);

    -- chunk metadata: narrative type + optional date (for search filters)
    ALTER TABLE document_chunks ADD COLUMN chunk_type VARCHAR(40);
    ALTER TABLE document_chunks ADD COLUMN effective_date DATE;
        """
    )


def downgrade() -> None:
    op.execute(
        """
    DROP INDEX IF EXISTS idx_chunks_fts;
    DROP INDEX IF EXISTS idx_documents_fts;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS chunk_type;
    ALTER TABLE document_chunks DROP COLUMN IF EXISTS effective_date;
    ALTER TABLE documents DROP COLUMN IF EXISTS extracted_tsv;
        """
    )
