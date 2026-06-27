# RAGAS Evaluation — latest

**Run:** 2026-06-27 18:55:08  
**Generation:** `mistralai/mistral-small-3.2-24b-instruct` · **Judge:** `google/gemini-3.1-flash-lite` · **top_k:** 8 · **chunk_size:** 1024  
**Questions:** 35 (errors: 0) · **Duration:** 1143.5s · **RAGAS:** 0.3.2

## Aggregate scores

_RAG-quality metrics averaged over the 30 answerable questions; the 5 adversarial (unanswerable) questions are measured by the refusal rate below._

| Metric | Score |
|---|---|
| faithfulness | 0.8056 |
| answer_relevancy | 0.8190 |
| llm_context_precision_with_reference | 0.7464 |
| context_recall | 0.9000 |

## By category

| Category | n | faithfulness | answer_relevancy | llm_context_precision_with_reference | context_recall |
|---|---|---|---|---|---|
| factual | 30 | 0.8056 | 0.8190 | 0.7464 | 0.9000 |

**Adversarial refusal rate:** 1.0000 (5 questions) — fraction of unanswerable questions the model correctly declined to answer.

## Notes

Per-question scores: `ragas_20260627_185508.json` (JSON) and the matching `.csv`.
