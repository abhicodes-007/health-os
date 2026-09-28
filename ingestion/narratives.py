"""Ingest of narrative texts into document_chunks (Phase 3, lean version without embeddings).

Narratives (consultation conclusions, immunogram interpretations, ultrasound descriptions) are
what's missing from structured observations: diagnostic reasoning, recommendations, context.
We store them as chunks with a full-text index; search via the `search` tool (tools.py).

One documents row = one physical file (unique file_sha256); chunks from different
consultations inside a single PDF attach to it. chunk_type + effective_date —
for search filters.
"""
from __future__ import annotations

import hashlib
import os

from sqlalchemy import text


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def upsert_document(conn, user_id: str, file_path: str, *, doc_type: str,
                    title: str, document_date: str | None = None,
                    extracted_text: str | None = None) -> str:
    """Creates/returns a documents row by file_sha256 (idempotent)."""
    sha = sha256_file(file_path) if os.path.exists(file_path) else hashlib.sha256(
        file_path.encode()).hexdigest()
    row = conn.execute(text("SELECT id FROM documents WHERE file_sha256=:s"),
                       {"s": sha}).first()
    if row:
        did = str(row[0])
        if extracted_text:
            conn.execute(text("UPDATE documents SET extracted_text=:t WHERE id=:id"),
                         {"t": extracted_text, "id": did})
        return did
    return str(conn.execute(
        text("""INSERT INTO documents (user_id, document_date, doc_type, title,
                    file_path, file_sha256, mime_type, extracted_text)
                VALUES (:u, :d, :dt, :ti, :fp, :sha, 'application/pdf', :txt)
                RETURNING id"""),
        {"u": user_id, "d": document_date, "dt": doc_type, "ti": title,
         "fp": file_path, "sha": sha, "txt": extracted_text},
    ).scalar())


def add_chunks(conn, document_id: str, chunks: list[dict]) -> int:
    """Adds chunks to a document (idempotent by (document_id, chunk_index)).

    chunk: {content, chunk_type?, effective_date?}. Before inserting, clears this document's
    old chunks so a re-import doesn't duplicate.
    """
    conn.execute(text("DELETE FROM document_chunks WHERE document_id=:d"),
                 {"d": document_id})
    for i, ch in enumerate(chunks):
        conn.execute(
            text("""INSERT INTO document_chunks
                        (document_id, chunk_index, content, chunk_type, effective_date)
                    VALUES (:d, :i, :c, :ct, :ed)"""),
            {"d": document_id, "i": i, "c": ch["content"],
             "ct": ch.get("chunk_type"), "ed": ch.get("effective_date")},
        )
    return len(chunks)
