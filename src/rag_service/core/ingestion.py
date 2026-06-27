"""Ingestion into ONE corpus-wide Chroma collection.

Shape vs. rag-service: documents no longer live in isolated `doc_<id>`
collections — every chunk lands in the single `settings.collection_name`
collection so retrieval spans the whole corpus. Re-ingesting a document is
idempotent *for that document only*: its old chunks are dropped by metadata
filter, the rest of the corpus is untouched.

`run_ocr` + the PDF helpers below stay as the PDF path. Other formats (XLSX /
DOCX / URL) come through `core/loaders.py`, which normalises them to text and
calls `ingest_text` — so everything downstream (chunk → embed → store) is
format-agnostic. The tagging+triples pass (graph layer) hooks into `ingest_text`
in the next build step (CLAUDE.md §7, Hours 1–3).
"""

import hashlib
import io
import logging

import chromadb
import fitz
import PIL.Image
from google import genai
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.chroma import ChromaVectorStore

from rag_service.config import settings
from rag_service.retry import with_retry

logger = logging.getLogger(__name__)

_OCR_PROMPT = "Extract all text and tables from this page as clean Markdown. Nothing else."


# --- PDF text / OCR path ----------------------------------------------------


def _pdf_to_images(pdf_bytes: bytes) -> list[tuple[int, bytes]]:
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [
        (i, pdf.load_page(i).get_pixmap(matrix=fitz.Matrix(1.0, 1.0)).tobytes("png"))
        for i in range(len(pdf))
    ]
    pdf.close()
    return pages


def _extract_text_directly(pdf_bytes: bytes) -> str | None:
    # Return embedded text if substantial; None means PDF is scanned, fall back to OCR.
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [pdf.load_page(i).get_text() for i in range(len(pdf))]
    n_pages = len(pages)
    pdf.close()
    combined = "\n\n".join(f"--- Page {i + 1} ---\n\n{t}" for i, t in enumerate(pages))
    if n_pages == 0 or len(combined) < 50 * n_pages:
        return None
    return combined


def _ocr_page(i: int, img_bytes: bytes, client: genai.Client) -> str:
    img = PIL.Image.open(io.BytesIO(img_bytes))

    def _call() -> str:
        response = client.models.generate_content(
            model=settings.ocr_model,
            # genai accepts a PIL image at runtime; its stubs don't model that.
            contents=[_OCR_PROMPT, img],  # type: ignore[arg-type]
        )
        return response.text or ""

    # Retries 429 (rate limit) and transient 500/503 — one flaky page would
    # otherwise abort the whole document mid-ingest.
    return with_retry(_call, what=f"OCR page {i + 1}")


def run_ocr(pdf_bytes: bytes) -> str:
    """Extract a PDF as Markdown. Try embedded text first; OCR only for scans."""
    direct = _extract_text_directly(pdf_bytes)
    if direct is not None:
        logger.info("extracted text directly, skipping OCR")
        return direct

    logger.info("no embedded text found, running OCR")
    client = genai.Client(api_key=settings.gemini_api_key)
    pages = _pdf_to_images(pdf_bytes)
    results: dict[int, str] = {}
    for i, img_bytes in pages:
        results[i] = _ocr_page(i, img_bytes, client)
        logger.info("ocr page %d/%d done", i + 1, len(pages))
    return "\n\n".join(f"--- Page {i + 1} ---\n\n{results[i]}" for i in sorted(results))


# --- Corpus-wide storage ----------------------------------------------------


def _store_nodes(nodes: list[BaseNode], document_id: str) -> None:
    """Upsert nodes into the shared corpus collection, idempotent per document.

    Drops only *this* document's prior chunks (by metadata filter) so a
    re-ingest doesn't duplicate, while leaving the rest of the corpus intact.
    """
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(settings.collection_name)
    try:
        collection.delete(where={"document_id": document_id})
    except Exception:
        pass  # nothing to delete on first ingest of this doc
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(nodes, storage_context=storage_context)

    # New/changed chunks make the in-memory BM25 index stale → force a rebuild
    # on the next query (lazy import avoids a circular dependency).
    from rag_service.core import retrieval

    retrieval.invalidate()


def ingest_text(
    text: str,
    document_id: str,
    source: str,
    extra_metadata: dict | None = None,
) -> int:
    """Chunk pre-extracted text, embed, and store in the corpus. Returns chunk count.

    This is the format-agnostic entry point: PDF/XLSX/DOCX/URL loaders all
    normalise to text and call here.
    """
    metadata = {"document_id": document_id, "source": source}
    if extra_metadata:
        metadata.update(extra_metadata)

    nodes = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    ).get_nodes_from_documents([Document(text=text, metadata=metadata)])

    # Single LLM tagging+triples pass: tags → chunk metadata, spec/relation
    # triples → the graph (curated spec nodes are skipped inside add_extraction).
    if settings.enable_graph_extraction:
        from rag_service.core import extraction, graph

        for node in nodes:
            ex = extraction.extract(node.get_content())
            for k, v in (ex.tags or {}).items():
                if v:
                    node.metadata[k] = v
            graph.add_extraction(node.node_id, source, ex.specs, ex.relations, persist=False)
        graph.save()

    _store_nodes(nodes, document_id)
    logger.info("ingested document_id=%s source=%s chunks=%d", document_id, source, len(nodes))
    return len(nodes)


def ingest_document(pdf_bytes: bytes, document_id: str, source: str = "upload.pdf") -> int:
    """OCR/extract a PDF, then ingest it into the corpus. Returns chunk count."""
    md_text = run_ocr(pdf_bytes)
    return ingest_text(md_text, document_id, source)


def content_id(data: bytes) -> str:
    """Stable document ID derived from raw content (any format)."""
    return hashlib.md5(data).hexdigest()[:12]


# Back-compat alias: rag-service called this `pdf_content_id`.
pdf_content_id = content_id
