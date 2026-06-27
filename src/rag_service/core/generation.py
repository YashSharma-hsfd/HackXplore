from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llama_index.core.schema import NodeWithScore
from openai import OpenAI

from rag_service.config import settings
from rag_service.retry import with_retry

# Bilingual (DE/EN) engine-expert prompt. Mistral Small 3.2 is multilingual, so
# we instruct it to answer in the question's language and to quote exact specs
# (jet sizes, clearances, torque) verbatim — the whole point of the BM25 half of
# hybrid retrieval is that those exact tokens survive to the answer.
_PROMPT = """\
You are an expert assistant for TWO-STROKE engines (maintenance, tuning, troubleshooting),
plus the fuels, lubricants and performance fundamentals that apply to them.
Answer the QUESTION using ONLY the CONTEXT below (forum posts, manuals, spec sheets).

Rules:
- SCOPE: Your domain is two-stroke engines. If the question asks specifically about
  FOUR-STROKE engines (e.g. the four-stroke cycle, or a value defined only for a
  four-stroke engine), or is unrelated to engines/fuels, DECLINE with the refusal
  sentence below — even if the CONTEXT happens to contain the answer. A comparison
  made to explain a two-stroke is in scope; a four-stroke-only fact is not.
- Quote exact specifications (jet sizes, clearances, torque values, part numbers) verbatim when they appear.
- Answer in the SAME LANGUAGE as the question (German or English) — this includes refusals.
- If you cannot or should not answer, say so plainly, in the question's language:
  EN: "I don't have enough information." / DE: "Ich habe nicht genügend Informationen."
- Be concise and practical.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


@dataclass
class GenerationResult:
    """Output of one generation call, including token usage for cost tracking."""

    answer: str
    citations: list[dict[str, Any]]
    model: str
    prompt_tokens: int
    output_tokens: int


def _client() -> OpenAI:
    """OpenAI-compatible client pointed at the configured LLM provider.

    Defaults to OpenRouter (reusing OPENROUTER_API_KEY); `llm_api_key` overrides
    when serving Mistral directly or via a local vLLM/Ollama endpoint.
    """
    api_key = settings.llm_api_key or settings.openrouter_api_key
    return OpenAI(api_key=api_key, base_url=settings.llm_base_url)


def _to_citation(node: NodeWithScore) -> dict[str, Any]:
    """Shape a retrieved node into a UI/edit-friendly citation.

    `chunk_id` is the Chroma/LlamaIndex node id — the UI passes it back to
    `PATCH /chunk/{chunk_id}` for the maintenance flow (CLAUDE.md §5).
    """
    meta = node.node.metadata or {}
    return {
        "chunk_id": node.node.node_id,
        "source": meta.get("source") or meta.get("document_id", ""),
        "title": meta.get("title", ""),
        "score": float(node.score) if node.score is not None else 0.0,
        "snippet": node.node.get_content()[:280],
    }


def generate(
    question: str, nodes: list[NodeWithScore], facts: list[dict] | None = None
) -> GenerationResult:
    """Call Mistral (via OpenRouter) with retrieved context + canonical graph facts.

    The call is wrapped in ``with_retry`` so transient 5xx / 429 rate limits
    don't kill a user-facing /query (or an eval question) on the first hiccup.
    """
    context = "\n\n".join(node.node.get_content() for node in nodes)
    if facts:
        facts_text = "\n".join(
            f"- {f.get('subject', '')} {f.get('attribute', '')}: "
            f"{f.get('value', '')} {f.get('unit', '')}".strip()
            for f in facts
        )
        context = (
            "KNOWN FACTS (authoritative — prefer these exact values):\n"
            f"{facts_text}\n\n---\n\n{context}"
        )
    citations = [_to_citation(node) for node in nodes]

    client = _client()
    response = with_retry(
        lambda: client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "user", "content": _PROMPT.format(context=context, question=question)}
            ],
            temperature=0.1,
            max_tokens=1000,  # bound output cost; plenty for a cited engine answer
        ),
        what="mistral generation",
    )

    usage = response.usage
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    answer = (response.choices[0].message.content or "").strip()

    return GenerationResult(
        answer=answer,
        citations=citations,
        model=settings.llm_model,
        prompt_tokens=prompt_tokens,
        output_tokens=output_tokens,
    )
