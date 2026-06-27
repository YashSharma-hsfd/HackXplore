from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from rag_service.api.schemas import (
    ChunkEditRequest,
    FactEditRequest,
    GraphFact,
    HealthResponse,
    IngestResponse,
    IngestUrlRequest,
    MetricsResponse,
    QueryRequest,
    QueryResponse,
    TipRequest,
)
from rag_service.cache.redis_cache import stats as cache_stats
from rag_service.core import graph, maintenance
from rag_service.core.ingestion import content_id, ingest_text
from rag_service.core.loaders import load_bytes, load_url
from rag_service.core.pipeline import query_pipeline
from rag_service.observability.cost_tracker import tracker as cost_tracker

router = APIRouter()

# A minimal demo page is served at "/"; the full interactive API stays at "/docs".
# Read once at import — the file ships in the image (the Dockerfile copies src/).
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_INDEX_HTML = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")


@router.get("/", include_in_schema=False, response_class=HTMLResponse)
def root() -> HTMLResponse:
    return HTMLResponse(_INDEX_HTML)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/metrics", response_model=MetricsResponse)
async def metrics() -> MetricsResponse:
    return MetricsResponse(
        cache_hits=cache_stats.hits,
        cache_misses=cache_stats.misses,
        cache_hit_rate=cache_stats.hit_rate(),
        **cost_tracker.snapshot(),
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest(file: UploadFile = File(...)) -> IngestResponse:
    """Ingest an uploaded file. Dispatches by extension (PDF / XLSX / DOCX / TXT /
    HTML) via core/loaders.py, then runs the shared corpus pipeline."""
    data = file.file.read()
    filename = file.filename or "upload"
    try:
        text = load_bytes(data, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    document_id = content_id(data)
    n_chunks = ingest_text(text, document_id, source=filename)
    return IngestResponse(document_id=document_id, source=filename, n_chunks=n_chunks)


@router.post("/ingest-url", response_model=IngestResponse)
def ingest_url(body: IngestUrlRequest) -> IngestResponse:
    """Ingest a web page (forum thread / article) by URL via main-content extraction."""
    try:
        text = load_url(body.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    document_id = content_id(body.url.encode("utf-8"))
    n_chunks = ingest_text(text, document_id, source=body.url, extra_metadata={"type": "web"})
    return IngestResponse(document_id=document_id, source=body.url, n_chunks=n_chunks)


@router.post("/tip", response_model=IngestResponse)
def submit_tip(body: TipRequest) -> IngestResponse:
    """Add a free-text tip to the corpus (the contribution loop) — immediately searchable."""
    document_id = content_id(body.text.encode("utf-8"))
    n_chunks = ingest_text(body.text, document_id, source=body.source, extra_metadata={"type": "tip"})
    return IngestResponse(document_id=document_id, source=body.source, n_chunks=n_chunks)


@router.post("/query", response_model=QueryResponse)
def query(body: QueryRequest) -> QueryResponse:
    try:
        result = query_pipeline(
            question=body.question, top_k=body.top_k, web_search=body.web_search
        )
    except RuntimeError as e:
        # e.g. web search requested but TAVILY_API_KEY is unset.
        raise HTTPException(status_code=503, detail=str(e))
    return QueryResponse(**result)


@router.get("/graph")
def graph_view(limit: int = 400) -> dict:
    """The knowledge graph as nodes/edges JSON for the vis.js panel (capped for size)."""
    vis = graph.to_vis()
    if len(vis["nodes"]) > limit:
        keep = {n["id"] for n in vis["nodes"][:limit]}
        vis = {
            "nodes": vis["nodes"][:limit],
            "edges": [e for e in vis["edges"] if e["from"] in keep and e["to"] in keep],
        }
    return {**vis, "stats": graph.stats()}


@router.get("/related")
def related(entity: str, depth: int = 1) -> dict:
    """Graph neighbours of an entity — the recommendation ('related topics') feature."""
    return {"entity": entity, "related": graph.neighbors(entity, depth)}


@router.patch("/chunk/{chunk_id}")
def edit_chunk(chunk_id: str, body: ChunkEditRequest) -> dict:
    """Edit a chunk's text and/or metadata (re-embeds + rebuilds BM25 + re-extracts
    triples only if text changed). `chunk_id` comes from a citation's `chunk_id`."""
    if body.new_text is None and body.new_metadata is None:
        raise HTTPException(status_code=400, detail="provide new_text and/or new_metadata")
    try:
        return maintenance.update_chunk(
            chunk_id, new_text=body.new_text, new_metadata=body.new_metadata
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no such chunk: {chunk_id}")


@router.patch("/fact", response_model=GraphFact)
def edit_fact(body: FactEditRequest) -> GraphFact:
    """Edit a structured fact in one shot (graph node) and flag it curated (§5)."""
    try:
        node = graph.update_fact(body.id, body.new_value)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"no such fact node: {body.id}")
    return GraphFact(
        id=node["id"],
        subject=node.get("subject", ""),
        attribute=node.get("attribute", ""),
        value=node.get("value", ""),
        unit=node.get("unit", ""),
        curated=bool(node.get("curated", False)),
    )
