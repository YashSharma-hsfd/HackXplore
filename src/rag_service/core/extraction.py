"""LLM tagging + triples extraction — the graph-lite ingest pass.

One Mistral call per chunk returns compact JSON: metadata tags + spec triples
(subject, attribute, value) + relation triples (subject, relation, object).
Tight prompt, low max_tokens, temperature 0 → cheap and deterministic. Parsing
is defensive: malformed output yields empty results rather than failing ingest.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from openai import OpenAI

from rag_service.config import settings
from rag_service.retry import with_retry

logger = logging.getLogger(__name__)

_PROMPT = """You extract structured knowledge about two-stroke / piston engines from a text chunk \
(the text may be German or English).
Return ONLY one compact JSON object, no prose, with EXACTLY this shape:
{{
  "tags": {{"engine_model": "", "topic": "", "part": "", "symptom": ""}},
  "specs": [{{"subject": "", "attribute": "", "value": "", "unit": ""}}],
  "relations": [{{"subject": "", "relation": "", "object": ""}}]
}}
Rules:
- "topic" is one of: maintenance, tuning, troubleshooting, reference.
- "specs": ONLY explicit measurable values actually present (e.g. jet size, clearance,
  torque, temperature, heating value, pressure). At most 12, most important first.
  Empty list if none. Do NOT invent values.
- "relations": meaningful entity links (e.g. part-of, causes, requires, affects). Empty if none.
- Keep subjects/attributes short and canonical; use the text's own units; leave a field "" if unknown.

TEXT:
{text}

JSON:"""


@dataclass
class Extraction:
    tags: dict = field(default_factory=dict)
    specs: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)


def _client() -> OpenAI:
    return OpenAI(
        api_key=settings.llm_api_key or settings.openrouter_api_key,
        base_url=settings.llm_base_url,
    )


def _parse(content: str) -> Extraction:
    s = (content or "").strip()
    # Strip code fences if the model wrapped the JSON.
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        return Extraction()
    try:
        data = json.loads(s[start : end + 1])
    except Exception as e:
        logger.warning("extraction JSON parse failed: %s", e)
        return Extraction()

    tags = data.get("tags") if isinstance(data.get("tags"), dict) else {}
    specs = [
        x
        for x in (data.get("specs") or [])
        if isinstance(x, dict) and str(x.get("subject", "")).strip() and str(x.get("value", "")).strip()
    ]
    relations = [
        x
        for x in (data.get("relations") or [])
        if isinstance(x, dict) and str(x.get("subject", "")).strip() and str(x.get("object", "")).strip()
    ]
    return Extraction(tags=tags, specs=specs, relations=relations)


def extract(text: str) -> Extraction:
    """Run the tagging+triples pass over one chunk. Never raises on bad output."""
    client = _client()
    try:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=settings.llm_model,
                messages=[{"role": "user", "content": _PROMPT.format(text=text[:4000])}],
                temperature=0,
                max_tokens=1200,
                response_format={"type": "json_object"},
            ),
            what="graph extraction",
        )
    except Exception as e:
        logger.warning("extraction call failed, skipping chunk: %s", e)
        return Extraction()
    return _parse(resp.choices[0].message.content or "")
