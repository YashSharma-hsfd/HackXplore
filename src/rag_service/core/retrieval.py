"""Corpus-wide hybrid retrieval.

Dense (Chroma vectors, BGE-M3) + sparse (BM25 over the same chunks) fused with
Reciprocal Rank Fusion, then a cross-encoder reranker trims the pool to the
final top-k. One shared `corpus` collection, so a query spans every ingested
document — manuals, spec sheets, forum threads.

Why this shape (CLAUDE.md §2): BM25 nails exact technical tokens (jet sizes,
part numbers, German compound terms like *Schallgeschwindigkeit*); dense handles
paraphrase; the reranker fixes ordering. RRF runs with `num_queries=1` + a
`MockLLM`, so fusion is pure rank math — no LLM query-generation, zero tokens.

The engine is built once and cached; `invalidate()` drops it so the next query
rebuilds after an ingest/edit (the BM25 index is in-memory over the corpus
nodes, and the cross-encoder model loads once here rather than per query).
"""

from __future__ import annotations

import logging

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.llms import MockLLM
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.vector_stores.chroma import ChromaVectorStore

from rag_service.config import settings

logger = logging.getLogger(__name__)

_engine: "_HybridEngine | None" = None


def _collection():
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return client.get_or_create_collection(settings.collection_name)


def _load_all_nodes(collection) -> list[TextNode]:
    """Pull every chunk out of Chroma as TextNodes to feed the in-memory BM25 index."""
    got = collection.get(include=["documents", "metadatas"])
    ids = got.get("ids") or []
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    nodes: list[TextNode] = []
    for i, _id in enumerate(ids):
        text = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        nodes.append(TextNode(text=text or "", id_=_id, metadata=meta or {}))
    return nodes


class _HybridEngine:
    """Dense + BM25 → RRF fusion → cross-encoder rerank. Built once, cached."""

    def __init__(self) -> None:
        collection = _collection()
        index = VectorStoreIndex.from_vector_store(
            ChromaVectorStore(chroma_collection=collection)
        )
        dense = index.as_retriever(similarity_top_k=settings.fusion_top_k)

        nodes = _load_all_nodes(collection)
        if nodes:
            bm25 = BM25Retriever.from_defaults(
                nodes=nodes, similarity_top_k=settings.bm25_top_k
            )
            # num_queries=1 + MockLLM => pure RRF, no LLM query-gen, zero tokens.
            self._retriever = QueryFusionRetriever(
                [dense, bm25],
                llm=MockLLM(),
                similarity_top_k=settings.fusion_top_k,
                num_queries=1,
                mode="reciprocal_rerank",
                use_async=False,
            )
        else:
            self._retriever = dense  # empty corpus: nothing to fuse

        self._reranker = SentenceTransformerRerank(
            model=settings.reranker_model, top_n=settings.rerank_top_n
        )
        logger.info("hybrid engine built: %d nodes", len(nodes))

    def retrieve(self, query: str, top_k: int) -> list[NodeWithScore]:
        candidates = self._retriever.retrieve(query)
        if not candidates:
            return []
        reranked = self._reranker.postprocess_nodes(
            candidates, query_bundle=QueryBundle(query)
        )
        return reranked[:top_k]


def _get_engine() -> "_HybridEngine":
    global _engine
    if _engine is None:
        _engine = _HybridEngine()
    return _engine


def invalidate() -> None:
    """Drop the cached engine so the next query rebuilds (call after ingest/edit)."""
    global _engine
    _engine = None


def retrieve(query: str, top_k: int) -> list[NodeWithScore]:
    """Corpus-wide hybrid retrieval: dense + BM25 (RRF) → reranked top-k."""
    return _get_engine().retrieve(query, top_k)
