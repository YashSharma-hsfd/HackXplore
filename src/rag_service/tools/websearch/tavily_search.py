"""Web-search tool — live web retrieval via Tavily (https://docs.tavily.com).

Used by the "web search" toggle on /query: when on, the bot answers from live
web results instead of the local corpus (web-only mode). Every external call
goes through ``with_retry`` (retry.py), like the embedding/generation paths,
so a transient 429/5xx doesn't kill the request.

Requires ``TAVILY_API_KEY`` in .env; until it's set, calling ``web_search``
raises a clear RuntimeError (the /query route turns that into a 503).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from tavily import TavilyClient

from rag_service.config import settings
from rag_service.retry import with_retry


@dataclass
class WebResult:
    """One web-search hit, shaped to drop straight into the generation context."""

    title: str
    url: str
    snippet: str
    score: float = 0.0


@lru_cache(maxsize=1)
def _client() -> TavilyClient:
    """Cached Tavily client. Fail loudly if the key is missing rather than
    letting the SDK emit a confusing auth error mid-request."""
    if not settings.tavily_api_key:
        raise RuntimeError(
            "TAVILY_API_KEY is not set — required for web search. Add it to .env."
        )
    return TavilyClient(api_key=settings.tavily_api_key)


def web_search(query: str, max_results: int = 5) -> list[WebResult]:
    """Query Tavily and return ranked web results (wrapped in ``with_retry``)."""
    client = _client()
    data = with_retry(
        lambda: client.search(
            query=query, max_results=max_results, search_depth="basic"
        ),
        what="tavily web search",
    )
    return [
        WebResult(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
            score=float(r.get("score", 0.0) or 0.0),
        )
        for r in data.get("results", [])
    ]
