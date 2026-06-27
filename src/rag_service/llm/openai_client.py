"""Global LlamaIndex wiring.

Embeddings are **BGE-M3** (`BAAI/bge-m3`) — multilingual (German + English),
run locally via `HuggingFaceEmbedding` (no API cost) — wrapped in the inherited
Redis read-through cache so identical chunks across the corpus aren't
re-embedded. (Filename kept from rag-service to minimise churn; nothing here
talks to OpenAI.)
"""

from llama_index.core import Settings as LlamaSettings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from rag_service.cache.redis_cache import CachingEmbedding, get_redis_client
from rag_service.config import settings


def setup_llamaindex_settings() -> None:
    """Configure global LlamaIndex settings. Call once at app startup.

    First call downloads BGE-M3 (~2.3GB) from Hugging Face; later runs load it
    from the local HF cache. `max_length` is raised to cover our chunk_size so
    long chunks aren't silently truncated at the default 512 tokens.
    """
    underlying = HuggingFaceEmbedding(
        model_name=settings.embedding_model,  # BAAI/bge-m3
        max_length=max(512, settings.chunk_size),
        normalize=True,  # cosine-ready vectors; BGE-M3 needs no instruction prefix
    )
    LlamaSettings.embed_model = CachingEmbedding(
        underlying=underlying,
        redis_client=get_redis_client(),
        cache_ttl=settings.cache_ttl,
        cache_model_name=settings.embedding_model,
    )
    LlamaSettings.chunk_size = settings.chunk_size
    LlamaSettings.chunk_overlap = settings.chunk_overlap
