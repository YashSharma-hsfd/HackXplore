from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from rag_service.api.routes import router
from rag_service.config import settings
from rag_service.llm.openai_client import setup_llamaindex_settings
from rag_service.observability.logging_setup import setup_logging
from rag_service.observability.request_log import RequestLogMiddleware
from rag_service.observability.sentry_setup import setup_sentry

setup_logging(level=settings.log_level)
setup_sentry(dsn=settings.sentry_dsn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_llamaindex_settings()
    yield


app = FastAPI(
    title="Hirth Knowledge Engine",
    description="Two-stroke engine knowledge API (hybrid RAG + knowledge graph)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS so the Angular SPA (a different origin, e.g. http://localhost:4200) can
# call the API from the browser. No credentials are used (auth is server-side
# via .env keys), so a wildcard origin is safe here. Tighten CORS_ORIGINS in
# .env (comma-separated) for production.
_cors = (
    ["*"]
    if settings.cors_origins.strip() == "*"
    else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLogMiddleware)
app.include_router(router)

# Serve the built React SPA (frontend/dist, baked into the image by the
# Dockerfile) at "/". Mounted AFTER the API router so /query, /graph, etc. still
# resolve to the API; everything else falls through to the SPA. Guarded so local
# dev without a build present just skips it (run the frontend via `vite` then).
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend_dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
