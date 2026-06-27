"""Multi-format loader front door.

Normalises **every** input format to text/Markdown, then hands off to the shared
`ingestion.ingest_text` pipeline (chunk → tag+triples → embed → corpus). One
front door means everything downstream is format-agnostic — see CLAUDE.md §9.

Supported: PDF (PyMuPDF + Gemini Vision OCR fallback) · XLSX/XLS (pandas, one row
per line — keeps spec tables structured for triple extraction) · DOCX (docx2txt)
· URL/HTML (trafilatura main-content extraction) · plain TXT/MD.

Heavy/optional deps (pandas, docx2txt, trafilatura) are imported lazily so this
module imports cleanly even if one isn't installed — you only pay for the
formats you actually use.
"""

from __future__ import annotations

import io
import logging
import os

from rag_service.core.ingestion import run_ocr

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".xls",
    ".docx",
    ".txt",
    ".md",
    ".html",
    ".htm",
}


def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


# --- per-format extractors --------------------------------------------------


def _load_xlsx(data: bytes) -> str:
    """Excel → text, one row per line.

    Read with ``header=None`` so every cell becomes content: these are
    engineering calculation sheets, not clean tables, so pandas' inferred
    headers are just ``Unnamed: N`` noise. Joining non-empty cells per row keeps
    labels next to their values (e.g. ``Temp [°C] | 343 | ...``) for retrieval
    and triple extraction, without the noise or repeated-prefix token waste.
    """
    import pandas as pd

    sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=str)
    lines: list[str] = []
    for sheet_name, df in sheets.items():
        df = df.fillna("")
        lines.append(f"## Sheet: {sheet_name}")
        for _, row in df.iterrows():
            cells = [str(v).strip() for v in row.tolist() if str(v).strip()]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def _load_docx(data: bytes) -> str:
    """Word .docx → plain text via docx2txt (accepts a file-like object)."""
    import docx2txt

    return docx2txt.process(io.BytesIO(data)) or ""


def _html_to_text(html: str) -> str:
    """HTML → main-content text via trafilatura (strips nav/ads/boilerplate)."""
    import trafilatura

    extracted = trafilatura.extract(html, include_comments=True, include_tables=True)
    return extracted or ""


# --- public API -------------------------------------------------------------


def load_bytes(data: bytes, filename: str) -> str:
    """Normalise an uploaded file (any supported format) to text/Markdown."""
    ext = _ext(filename)
    if ext == ".pdf":
        return run_ocr(data)
    if ext in (".xlsx", ".xls"):
        return _load_xlsx(data)
    if ext == ".docx":
        return _load_docx(data)
    if ext in (".txt", ".md"):
        return data.decode("utf-8", errors="ignore")
    if ext in (".html", ".htm"):
        return _html_to_text(data.decode("utf-8", errors="ignore"))
    if ext == ".doc":
        raise ValueError(
            "Legacy binary .doc isn't supported directly — convert to .docx first "
            "(e.g. `soffice --headless --convert-to docx file.doc`)."
        )
    raise ValueError(f"Unsupported file type {ext!r}. Supported: {sorted(SUPPORTED_EXTENSIONS)}")


def load_url(url: str) -> str:
    """Fetch a web page (forum thread / article) and return its main-content text."""
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Could not fetch URL: {url}")
    text = trafilatura.extract(downloaded, include_comments=True, include_tables=True)
    if not text:
        raise ValueError(f"No extractable content at URL: {url}")
    return text
