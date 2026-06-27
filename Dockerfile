# syntax=docker/dockerfile:1.7

# --- Builder: install deps with uv into an isolated .venv ---
FROM python:3.10-slim AS builder

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /usr/local/bin/uv

WORKDIR /app

# Install runtime deps first (cached when only source changes)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source and install the project itself
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Frontend builder: build the React/Vite app (frontend/) to static files ---
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# The SPA is served from this very Space, so point the build at the Space's own
# URL (its api.js falls back to localhost otherwise; CORS is open regardless).
ENV VITE_API_URL=https://Avishkar1117-engine.hf.space
RUN npm run build

# --- Runtime: slim image with only the venv + source ---
FROM python:3.10-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Bake the prebuilt corpus (vectors) + knowledge graph into the image so the
# deployed service answers immediately — HF Spaces has no host volume to mount,
# so the data must live in the image (kept out of .dockerignore for this).
COPY chroma_store/ /app/chroma_store/
COPY graph_store/ /app/graph_store/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1

RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "rag_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
