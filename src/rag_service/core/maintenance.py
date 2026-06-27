"""Chunk maintenance — the careful edit path (CLAUDE.md §5).

Editing free text inside a chunk must keep three derived stores in sync:
  - Chroma vector  → re-embed (only if text changed)
  - Chroma text    → patch the document
  - BM25 index     → rebuild (it indexes the text)  [via retrieval.invalidate()]
  - networkx graph → re-extract that chunk's triples

A metadata-only edit touches none of the embedding/BM25/graph machinery — it
just patches Chroma metadata. The structured-value edit (one graph node) lives
in `graph.update_fact`; this module is for prose edits.
"""

from __future__ import annotations

import logging

import chromadb
from llama_index.core import Settings as LlamaSettings

from rag_service.config import settings
from rag_service.core import extraction, graph, retrieval

logger = logging.getLogger(__name__)


def _collection():
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(settings.collection_name)


def update_chunk(
    chunk_id: str, new_text: str | None = None, new_metadata: dict | None = None
) -> dict:
    """Edit one chunk, keeping vector / text / BM25 / graph in sync.

    Re-embeds (and rebuilds BM25 + re-extracts triples) ONLY if the text
    changed; a metadata-only edit just patches Chroma. Raises KeyError if the
    chunk id is unknown.
    """
    col = _collection()
    got = col.get(ids=[chunk_id], include=["documents", "metadatas"])
    if not got["ids"]:
        raise KeyError(chunk_id)

    text = got["documents"][0]
    meta = dict(got["metadatas"][0] or {})
    if new_metadata:
        meta.update(new_metadata)
        # Chroma metadata values must be scalar (str/int/float/bool) — drop Nones.
        meta = {k: v for k, v in meta.items() if v is not None}

    text_changed = new_text is not None and new_text != text
    if text_changed:
        embedding = LlamaSettings.embed_model.get_text_embedding(new_text)
        col.update(
            ids=[chunk_id], documents=[new_text], embeddings=[embedding], metadatas=[meta]
        )
        # Graph: drop this chunk's old (non-curated) triples and re-extract.
        graph.remove_chunk(chunk_id)
        if settings.enable_graph_extraction:
            ex = extraction.extract(new_text)
            graph.add_extraction(chunk_id, meta.get("source", ""), ex.specs, ex.relations)
        retrieval.invalidate()  # BM25 indexes the text → force a rebuild
        text = new_text
    elif new_metadata:
        col.update(ids=[chunk_id], metadatas=[meta])

    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": meta,
        "reembedded": text_changed,
    }


def replace_value(old: str, new: str) -> list[str]:
    """Replace a literal value in EVERY chunk that contains it (a value can span
    multiple chunks). Returns the ids of the chunks updated."""
    col = _collection()
    got = col.get(where_document={"$contains": old}, include=["documents"])
    updated: list[str] = []
    for cid, doc in zip(got["ids"], got["documents"]):
        update_chunk(cid, new_text=doc.replace(old, new))
        updated.append(cid)
    return updated
