"""Local embeddings (Phase 3) — fastembed/ONNX, no torch (Python 3.13-compatible).

Model paraphrase-multilingual-mpnet-base-v2 (768d, uk/ru/en) — the dimension matches
document_chunks.embedding vector(768). Embeddings are L2-normalized → cosine via HNSW.
The model is local (first run downloads ~1 GB into the HF cache), offline, no API key.

The model loads lazily (singleton): the first embed in the MCP server process takes a few
seconds, then it's instant.
"""
from __future__ import annotations

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBED_DIM = 768

_model = None


def get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding  # heavy import — only when needed
        _model = TextEmbedding(MODEL_NAME)
    return _model


def _norm(v) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n else v


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    """L2-normalized vectors for a list of texts."""
    return [_norm(v) for v in get_model().embed(list(texts))]


def embed_one(text: str) -> np.ndarray:
    return _norm(next(iter(get_model().embed([text]))))


def to_pgvector(v) -> str:
    """Vector → pgvector literal '[...]' for the ::vector cast."""
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"
