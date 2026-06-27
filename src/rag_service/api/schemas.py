from pydantic import BaseModel, ConfigDict, Field

from rag_service.config import settings


class HealthResponse(BaseModel):
    status: str


class IngestResponse(BaseModel):
    document_id: str
    source: str
    n_chunks: int


class IngestUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(..., min_length=1)


class TipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)
    source: str = "user tip"


class ChunkEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_text: str | None = None
    new_metadata: dict | None = None


class QueryRequest(BaseModel):
    # Reject unknown fields so typos like `k` / `n_chunks` fail loudly instead of silently
    # falling back to the default `top_k`.
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1)
    # Corpus-wide: retrieval spans the whole `corpus` collection, so no
    # per-document scoping is required (dropped the old required `document_id`).
    # Default tracks settings.top_k so the .env TOP_K knob is the single source of truth.
    top_k: int = Field(default=settings.top_k, ge=1, le=20)
    # When true, answer from live web search (Tavily) instead of the local
    # corpus — the frontend "web search" toggle. Requires TAVILY_API_KEY.
    web_search: bool = False


class Citation(BaseModel):
    """One retrieved source. `chunk_id` is the Chroma node id the UI passes back
    to `PATCH /chunk/{chunk_id}` for the maintenance/edit flow (CLAUDE.md §5)."""

    chunk_id: str
    source: str
    title: str = ""
    score: float = 0.0
    snippet: str = ""
    # Web citations (from the web-search toggle) carry `source_type="web"` + a
    # `url`; corpus citations leave these at their defaults. The UI uses
    # `source_type` to render web hits distinctly (and `chunk_id` is empty for
    # web, since there's no editable chunk behind them).
    url: str = ""
    source_type: str = "corpus"


class GraphFact(BaseModel):
    """A canonical structured fact from the graph layer (an editable spec node)."""

    id: str
    subject: str = ""
    attribute: str = ""
    value: str = ""
    unit: str = ""
    curated: bool = False


class FactEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1)  # spec node id (e.g. "spec::jet a1::freezing point")
    new_value: str = Field(..., min_length=1)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    facts: list[GraphFact] = []
    latency_ms: int
    cost_usd: float


class MetricsResponse(BaseModel):
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    n_queries: int
    total_cost_usd_today: float
    mean_cost_usd_per_query: float
    p50_latency_ms: float
    p95_latency_ms: float
