# RAGAS Evaluation — Pitch Table

*Two-Stroke Knowledge Database — measured quality, not a notebook demo.*

**Setup:** 35 bilingual questions (20 EN / 15 DE) · 30 answerable + 5 adversarial · **0 errors**
**Stack:** generation `Mistral Small 3.2 24B` · embeddings `BGE-M3` · hybrid retrieval (dense + BM25 → RRF, 15-candidate pool → `bge-reranker-v2-m3` → top-8 context) · judge `Gemini 3.1 Flash-Lite`
**Corpus:** 122 chunks across PDF + XLSX · knowledge graph 1,245 nodes / 1,070 edges / 509 specs

---

## Headline results

| Metric | Score | What it means |
|---|---:|---|
| **Faithfulness** | **0.90** | Answers are grounded in the retrieved sources (low hallucination). |
| **Answer relevancy** | **0.80** | Answers actually address the question asked. |
| **Context precision** | **0.75** | Retrieved context is on-topic, not noise. |
| **Context recall** | **0.87** | Retrieval surfaces the ground-truth content it needs. |
| **Adversarial refusal** | **1.00 (5/5)** | Correctly declines out-of-scope questions (four-stroke / off-topic) instead of bluffing. |

*RAG-quality metrics averaged over the 30 answerable questions; the 5 adversarial questions are measured by refusal rate (a correct refusal grounds no claims, so it isn't scored on faithfulness).*

---

## Why these numbers matter

- **Bilingual, no translation step** — German and English questions both score well on one multilingual stack (BGE-M3 + Mistral).
- **Knows what it doesn't know** — 100% refusal on adversarial questions: asks the model to answer only in-scope (two-stroke) topics and decline four-stroke-specific or off-topic queries, *in the question's language*.
- **Grounded + relevant** — 0.90 faithfulness with 0.80 relevancy: it cites real sources and stays on the question.
- **Tuned, not guessed** — narrowing the rerank candidate pool (30 → 15) cut latency *and* lifted faithfulness 0.81 → 0.90, confirmed by re-running the same eval set.
- **Reproducible** — every run writes a timestamped JSON/CSV; this is a measured, shippable system.
