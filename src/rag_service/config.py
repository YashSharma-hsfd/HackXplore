import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Silence ChromaDB's anonymized telemetry — its capture() shim spams the logs
# with harmless errors that would otherwise clutter the demo output.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API keys ------------------------------------------------------------
    gemini_api_key: str = ""  # used only for the Gemini Vision OCR fallback on scanned PDFs
    github_token: str = ""
    github_model: str = "gpt-4o"
    github_api_base: str = "https://models.inference.ai.azure.com"

    # --- Generation LLM (chatbot answers + the ingest tagging/triples pass) ---
    # Mistral Small 3.2 24B — multilingual (German + English). Served
    # OpenAI-compatible via OpenRouter by default (reuses OPENROUTER_API_KEY
    # below). Point llm_base_url at Mistral's API or a local vLLM/Ollama
    # endpoint, and llm_model at the matching slug, to switch providers.
    llm_model: str = "mistralai/mistral-small-3.2-24b-instruct"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""  # if empty, generation falls back to openrouter_api_key

    # --- Embeddings ----------------------------------------------------------
    # BGE-M3 — multilingual, runs locally via sentence-transformers /
    # HuggingFaceEmbedding (no API cost), 1024-dim dense. PICK ONCE: changing
    # this = a different vector space ⇒ full corpus re-index (see CLAUDE.md §9).
    embedding_model: str = "BAAI/bge-m3"
    ocr_model: str = "gemini-3.1-flash-lite"

    # --- RAGAS judge ---------------------------------------------------------
    # `judge_provider` selects which provider's credentials + base URL +
    # default model the judge uses. Switching providers is a one-line .env
    # change; each provider's settings stay warm in code so you can flip
    # back and forth without re-discovering URLs and model slugs.
    #
    # Default "openrouter": the corpus + eval set are bilingual (DE/EN), so the
    # judge must be strong on German. We route a Gemini judge through OpenRouter
    # (paid) rather than the native Gemini API, because the Gemini *free* tier
    # gives 0 quota for the strong models (2.5-pro → limit 0) and rate-limits
    # the rest. Gemini is a *different* family from the Mistral generator, so
    # there's no faithfulness self-bias.
    #
    # Valid values: "deepseek" | "openrouter" | "gemini"
    judge_provider: str = "openrouter"

    # DeepSeek platform — https://platform.deepseek.com (OpenAI-compatible).
    # Available models per DeepSeek docs: deepseek-v4-flash (default),
    # deepseek-v4-pro, deepseek-chat / deepseek-reasoner (legacy, deprecated
    # 2026-07-24).
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_judge_model: str = "deepseek-v4-flash"

    # OpenRouter — https://openrouter.ai (OpenAI-compatible). This is the
    # DEFAULT judge route: a Gemini model served via OpenRouter (paid), which
    # sidesteps the native Gemini free-tier 0-quota limits.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_judge_model: str = "google/gemini-3.1-flash-lite"  # Gemini judge, bilingual

    # Gemini-as-judge (DEFAULT) — strong on German + English, a *different*
    # family from the Mistral generator (so no faithfulness self-bias), and it
    # runs on GEMINI_API_KEY so eval never spends OpenRouter credit.
    # `gemini_judge_model` is a working placeholder — set GEMINI_JUDGE_MODEL in
    # .env to the latest Gemini slug to upgrade (one-line change).
    gemini_judge_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_judge_model: str = "gemini-2.5-pro"

    chunk_size: int = 1024
    chunk_overlap: int = 50
    top_k: int = 8

    # --- Corpus-wide retrieval + hybrid + graph ------------------------------
    # ONE shared Chroma collection across all docs (vs. rag-service's per-doc
    # isolation) so retrieval spans the whole corpus. See CLAUDE.md §3/§9.
    collection_name: str = "corpus"
    bm25_top_k: int = 15  # sparse candidates
    fusion_top_k: int = 30  # vector+BM25 RRF candidate pool handed to the reranker
    reranker_model: str = "BAAI/bge-reranker-v2-m3"  # multilingual cross-encoder (DE/EN), local
    rerank_top_n: int = 8  # kept after rerank → generation context
    graph_store_path: str = "./graph_store/graph.json"  # networkx serialized to disk
    enable_graph_extraction: bool = True  # run the LLM tagging+triples pass at ingest

    # --- Web-search tool (RESERVED, not wired — see CLAUDE.md §12) ------------
    tavily_api_key: str = ""
    websearch_enabled: bool = False
    web_max_results: int = 5

    chroma_persist_dir: str = "./chroma_store"

    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 86400
    answer_cache_ttl: int = 3600

    sentry_dsn: str = ""
    log_level: str = "INFO"

    # CORS for the Angular SPA frontend. "*" (default) allows any origin;
    # set a comma-separated list (e.g. "http://localhost:4200") to restrict.
    cors_origins: str = "*"


# Required fields (gemini_api_key) are populated from the environment / .env;
# mypy can't see that, hence the ignore.
settings = Settings()  # type: ignore[call-arg]
