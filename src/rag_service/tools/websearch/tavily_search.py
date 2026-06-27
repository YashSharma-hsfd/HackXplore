"""Web-search tool — PLACEHOLDER, intentionally not implemented yet.

Reserved integration point for an OPTIONAL web-search fallback so the chatbot
can answer from the live web when the local corpus (graph + RAG) has nothing
relevant. Default provider: Tavily (https://docs.tavily.com).

Why it's a stub: we want the folder/structure reserved now so wiring it later
is "add the relevant files", not an architecture change. Do NOT build it yet —
it is tracked as future work in CLAUDE.md §12 (open decisions).

Wiring plan (when we pick it up):
  1. config.py  → add `tavily_api_key`, `websearch_enabled` (default False),
     `web_max_results` knobs (pydantic-settings, .env-driven, like every knob).
  2. implement `web_search()` below → call Tavily through `with_retry`
     (retry.py), the same wrapper every external call in this repo uses.
  3. core/pipeline.py → if corpus retrieval is empty / low-confidence AND
     `websearch_enabled`, call `web_search()` and merge `WebResult`s into the
     generation context as clearly-labelled WEB citations (kept visually
     distinct from corpus citations in the UI).
  4. record cost + latency in the tracker, like the embedding/generation paths.

Until implemented, importing this module is safe; calling `web_search()` raises.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WebResult:
    """One web-search hit, shaped to drop straight into the generation context."""

    title: str
    url: str
    snippet: str
    score: float = 0.0


def web_search(query: str, max_results: int = 5) -> list[WebResult]:
    """Return web results for a query. NOT IMPLEMENTED — reserved placeholder.

    Intended behaviour: query Tavily (wrapped in ``with_retry``) and return a
    list of ``WebResult``. See the module docstring for the wiring plan.
    """
    raise NotImplementedError(
        "web_search is a reserved placeholder and is not implemented for the "
        "hackathon. See the module docstring and CLAUDE.md §12."
    )
