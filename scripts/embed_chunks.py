"""Compute local embeddings for document_chunks (Phase 3).

Run (app-venv):  python -m scripts.embed_chunks
The model and normalization are in ingestion/embeddings.py (fastembed/ONNX, 768d, no torch).
Idempotent: encodes only chunks with embedding IS NULL.
"""
from __future__ import annotations

from sqlalchemy import text

from core.db import engine
from ingestion.embeddings import MODEL_NAME, embed_texts, to_pgvector


def main() -> None:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT id, content FROM document_chunks WHERE embedding IS NULL ORDER BY id")
        ).all()
        if not rows:
            print("No chunks without embeddings.")
            return
        print(f"Encoding {len(rows)} chunks with model {MODEL_NAME} (first run downloads ~1 GB)...")
        vecs = embed_texts([content for _id, content in rows])
        for (cid, _c), v in zip(rows, vecs):
            conn.execute(
                text("UPDATE document_chunks SET embedding=CAST(:e AS vector), embedding_model=:m WHERE id=:id"),
                {"e": to_pgvector(v), "m": MODEL_NAME, "id": cid},
            )
        n = conn.execute(
            text("SELECT count(*) FROM document_chunks WHERE embedding IS NOT NULL")
        ).scalar()
    print(f"Done. Embeddings in the database: {n}")


if __name__ == "__main__":
    main()
