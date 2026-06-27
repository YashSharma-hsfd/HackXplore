import time

import structlog

from rag_service.config import settings
from rag_service.core import graph
from rag_service.core.generation import generate, generate_web
from rag_service.core.retrieval import retrieve
from rag_service.observability.cost_tracker import estimate_cost, tracker
from rag_service.observability.request_log import request_id_var
from rag_service.tools.websearch import tavily_search

logger = structlog.get_logger(__name__)


def query_pipeline(question: str, top_k: int, web_search: bool = False) -> dict:
    """End-to-end RAG: retrieve → generate. Returns answer, citations, latency, cost.

    Two modes:
    - corpus (default): hybrid retrieval over the whole `corpus` collection +
      canonical graph specs.
    - web (`web_search=True`): answer from live Tavily results instead, skipping
      the local corpus and graph (the frontend "web search" toggle).

    Records cost + latency in the metrics tracker and emits one structured
    `query_completed` log event per call.
    """
    start = time.perf_counter()
    if web_search:
        results = tavily_search.web_search(question, max_results=settings.web_max_results)
        facts: list = []
        result = generate_web(question, results)
        n_context = len(results)
    else:
        nodes = retrieve(question, top_k)
        facts = graph.find_specs(question)[:12]  # canonical specs matching the query (capped)
        result = generate(question, nodes, facts=facts)
        n_context = len(nodes)
    latency_ms = int((time.perf_counter() - start) * 1000)

    cost_usd = estimate_cost(result.model, result.prompt_tokens, result.output_tokens)
    tracker.record(cost_usd, latency_ms)

    logger.info(
        "query_completed",
        request_id=request_id_var.get(),
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        output_tokens=result.output_tokens,
        n_retrieved=n_context,
        web_search=web_search,
    )
    return {
        "answer": result.answer,
        "citations": result.citations,
        "facts": [
            {
                "id": f.get("id", ""),
                "subject": f.get("subject", ""),
                "attribute": f.get("attribute", ""),
                "value": f.get("value", ""),
                "unit": f.get("unit", ""),
                "curated": bool(f.get("curated", False)),
            }
            for f in facts
        ],
        "latency_ms": latency_ms,
        "cost_usd": cost_usd,
    }
