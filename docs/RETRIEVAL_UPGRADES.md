# Retrieval Upgrade Plan: Reranking, Hybrid Search, Query Rewriting, GraphRAG

Design document, intentionally code-free: where each upgrade plugs into the
existing architecture, what data/config it adds, and the evaluation workflow
each change must follow. Written against the codebase as of the May 28 eval
baseline (`eval/results/ragas_20260528_155233.json`).

---

## 0. Verdict: the architecture absorbs all of this without restructuring

Every upgrade below is either a new **stage** in the pipeline or a new
**mode** behind the retrieval boundary. Nothing requires touching the API
contract, the generation step, the cache layer, or the eval harness logic.
That is because of five seams the codebase already has:

| Seam | Where | What plugs in there |
|---|---|---|
| Retrieval boundary | `core/retrieval.py`: `retrieve(document_id, query, top_k) → list[NodeWithScore]` | BM25, hybrid fusion, graph retrieval: anything that returns scored nodes |
| Pipeline stages | `core/pipeline.py`: `retrieve → generate` | a rerank stage between them; a query-rewrite stage before retrieval |
| Ingest side-artifacts | `core/ingestion.py`: OCR → chunk → embed → Chroma | sparse-index build and graph extraction, as parallel artifacts beside the vector store |
| Central config | `config.py` `Settings` | `retrieval_mode`, `rerank_*`, `rewrite_*`, `graph_*` knobs, all `.env`-switchable like `judge_provider` |
| Eval harness | `eval/run_ragas.py` calls the *same* `retrieve()`/`generate()` as production | every upgrade is automatically measured; new knobs get recorded in the report's `run` block |

Generation consumes `list[NodeWithScore]` opaquely, so it never changes.
The provider-pluggable pattern already proven on the RAGAS judge
(`deepseek | openrouter | gemini`) is the template to copy for the reranker
provider and the retrieval mode switch.

---

## Phase 0: prerequisites (about half a day, do before any experiment)

1. **Retriever factory.** `retrieval.py` currently constructs the Chroma
   client and index inline on every call. Restructure it into a small
   dispatcher: resolve the active mode from settings → build (and cache per
   `document_id` + mode) the underlying retriever → return nodes. The
   function signature the pipeline and the eval harness call stays exactly
   the same, so nothing upstream changes. This one-file refactor is what
   lets dense / sparse / hybrid / graph coexist as modes instead of forks.

2. **README aligned with the code (done 2026-06-10).** The README
   previously claimed a single shared Chroma collection (the code uses one
   per document), showed a `document_ids` list in the query example (the
   schema wants a single `document_id` string), listed the already-shipped
   generation retry as future work, and called the answer cache "wired"
   when only its TTL setting exists. All four are fixed; kept here for the
   record because each was the kind of drift that erodes trust in the
   baseline documentation new experiment rows will sit on.

3. **Protect the private files.** `CLAUDE.md` and `projects_roadmap_v3.pdf`
   are untracked but **not** listed in `.gitignore`, so one careless
   `git add -A` publishes them. Add both to `.gitignore` now. (CLAUDE.md
   also still carries the stale claims fixed in the README; worth a pass
   since it is the private source of truth.)

4. **Write down the eval-vs-prod scope difference.** The eval ingests all
   three PDFs into one collection (`doc_eval_corpus`) and searches
   corpus-wide; production `/query` is scoped to a single document. The
   eval numbers therefore measure a slightly harder retrieval problem
   (more distractor chunks). Fine, but state it in `eval/README.md` so
   every experiment inherits the caveat once instead of rediscovering it.

---

## 1. The shared experiment workflow (every upgrade follows this loop)

The eval harness is the project's spine. Each upgrade is **one config knob,
one eval run, one documented delta**, never a big-bang change:

1. **Freeze the baseline.** The May 28 run is experiment row 0.
2. **Implement behind a config flag, default off.** Merged code with the
   flag off must reproduce the baseline; the CI regression gate
   (`tests/eval/test_regression.py`, faithfulness >= 0.85) proves it.
3. **Unit-test with fakes** (no API calls), mirroring the existing test
   style: fake retrievers returning fixed nodes, fake rerankers returning
   fixed scores.
4. **One full 50-question run with the flag on.** A full run takes ~25 min
   and the free-tier quotas realistically allow **one full run per day**
   (CLAUDE.md section 9), so schedule experiments accordingly and use
   `--limit` smoke runs to debug before spending the daily run.
5. **Record per run:** aggregate deltas, per-category deltas (factual /
   multihop / adversarial), named cases (q050 is the standing probe),
   latency p50/p95 delta, and cost delta if any priced component is added.
6. **Document:** one new row in the README experiment table; the new knobs
   recorded in the report `run` block (extend `build_report()`'s run dict,
   the only harness change any upgrade needs).
7. **Decide:** win → flip the default, keep the old mode available for
   ablation; loss → keep the flag off and write the negative result down
   anyway. A documented "hybrid didn't help on this corpus because..." is
   worth nearly as much in an interview as a win.

Adversarial refusal rate must be watched on every run. It is currently a
perfect 1.00 and is the easiest metric to silently regress when retrieval
gets more aggressive (wider fetch → more plausible-looking context → fewer
refusals).

---

## 2. Upgrade A: cross-encoder reranking (do first)

**What and why.** Retrieve wide (fetch ~20), rerank with a cross-encoder
that scores each (question, chunk) pair jointly, keep the best 8. This
directly attacks the two weaknesses the baseline already names:
`context_precision` 0.7574 (the honest-judge number) and q050, where
retrieval reliably surfaces only half the needed facts. Widening the fetch
raises recall; the reranker restores precision.

**Where it plugs in.** New module `core/rerank.py`; the pipeline order
becomes `retrieve(fetch_k) → rerank → keep top_k → generate`. No ingestion
change, no storage change, no API change. The eval harness picks it up
automatically because `answer_question()` runs the same pipeline functions.

**Provider choice: copy the judge pattern.** `rerank_provider: none |
local | cohere` (or Jina):
- *Local* (`bge-reranker-base` family): no key, no external dependency;
  costs ~300 MB image size, slower cold start on the HF Space, and 1-3 s
  CPU latency for 20 pairs.
- *Hosted* (Cohere Rerank / Jina): fast and light in the image; adds an API
  key and an external dependency; free tiers exist but are capped.
- Recommendation: provider-pluggable from day one, local as the default for
  eval reproducibility, hosted as the Space option if cold start matters.

**Config.** `rerank_provider`, `fetch_k` (default 20), existing `top_k`
unchanged as the keep-count.

**Eval focus.** Expect `context_precision` up and multihop `context_recall`
up (the 8 to 20 fetch widens the funnel); q050 should flip from refusal to
answer, and that deserves a named callout in the README when it does.
Report the latency delta honestly; reranking is the one upgrade that
visibly costs p50.

**Gotchas.** The cost tracker prices generation only, so either add
reranker pricing or state it is unpriced. If `fetch_k` is ever exposed
per-request, the schema's `top_k <= 20` cap needs a matching bound.

---

## 3. Upgrade B: hybrid retrieval (BM25 + dense, score fusion)

**What and why.** Dense embeddings miss exact-term matches (model names,
"BLEU", "N = 6"); BM25 misses paraphrases. Fusing both is the standard
fix, and the corpus (technical papers, heavy in jargon and numbers) is
exactly where sparse helps.

**Design decision 1: where the sparse index lives.** Build it at ingest
and persist it per document beside `chroma_store/`, with the **same
delete-and-rebuild lifecycle** as the Chroma collection. The stale-Chroma
incident in the README generalizes: vector and sparse index must rebuild
together or they silently diverge. (The lazy alternative, rebuilding BM25
at query time from the chunk text Chroma already stores with an in-process
cache, needs zero persistence changes and is acceptable for eval, but it
reintroduces exactly the staleness class the project already got burned
by; not for production.)

**Design decision 2: fusion method.** Reciprocal Rank Fusion as the
default: scale-free, no score normalization (BM25 and cosine scores are
not comparable), effectively no hyperparameters. Weighted-sum with a tuned
alpha is an optional *second* experiment (an alpha sweep = one more
documented row). LlamaIndex's fusion retriever supports both modes, so
this stays inside the existing orchestration layer.

**Run it as a 3-way ablation.** `retrieval_mode: dense | sparse | hybrid`.
Three rows (dense baseline, BM25-only, hybrid) make a far stronger
write-up than two, and sparse-only is free once hybrid exists.

**Config.** `retrieval_mode`, fusion mode/constants. Record the tokenizer
choice (stemming on/off) in the report `run` block for reproducibility.

**Eval focus.** Factual-slice precision/recall is where the win should
show; watch paraphrase-heavy questions for regressions; the per-category
table tells the story either way.

**Scoping note.** One sparse index per `doc_{document_id}` mirrors the
per-document collections; the eval corpus is one collection, hence one
corpus-wide sparse index, consistent with the current eval scope.

---

## 4. Upgrade C: query rewriting (cheap add-on after B)

**What and why.** An LLM pass over the question before retrieval. Two
modes worth having: *multi-query expansion* (2-3 paraphrases or
sub-questions, retrieve each, fuse the results) and *HyDE* (embed a
hypothetical answer instead of the question). Multi-hop questions are the
target; they fail when no single query surfaces both hops.

**Where it plugs in.** New `core/query_transform.py`, a stage before
retrieval in the pipeline. Key structural point: multi-query **reuses the
fusion machinery from Upgrade B**. Variants are just extra queries into
the same fuser, so the marginal structure is near zero if B lands first.

**Cost control.** +1 LLM call per query (latency + free-tier quota). Cache
rewrites in Redis keyed by question hash; the embedding-cache pattern is
already there to copy. Default off (`query_rewrite: off | multi | hyde`).

**Eval focus.** Multihop slice and `answer_relevancy`. Known failure mode:
query drift hurting precise factual questions. The per-category table will
expose it, and a documented negative result is still a result.

---

## 5. Upgrade D: GraphRAG (do last, scope tightly)

**Honest scoping.** Full Microsoft-style GraphRAG (community detection +
hierarchical summaries) is a project of its own. The architecture-
compatible version is a **property-graph index**: at ingest, an LLM
extracts entity-relation triplets from the same chunks; at query time, a
graph retriever (entity/synonym expansion walking the graph, optionally
combined with vector hits) returns context, still as scored nodes, so the
pipeline contract is intact.

**Where it plugs in.**
- Ingestion: an optional graph-build step behind `graph_enabled`
  (default off, since it multiplies ingest cost), writing a per-document
  graph store beside `chroma_store/` with the same rebuild lifecycle.
- Retrieval: `retrieval_mode: graph` (and `graph+vector` combined) inside
  the Phase-0 factory.
- Chroma stays; the graph is additive, never a replacement.

**Cost reality.** Triplet extraction is roughly one LLM call per chunk, so
a few hundred calls to build the eval corpus graph, brushing the free-tier
daily caps. The mitigations are already house style: `with_retry` treats
429s as quota waits, and extraction results should be Redis-cached per
chunk hash so rebuilds are free.

**Eval focus.** Compare graph vs dense vs hybrid **on the multihop slice
specifically**; that is the published motivation for GraphRAG. Hard
prerequisite: the multihop slice is only 10 questions, so expand it to
15-20 first or the deltas drown in noise. q050 is again the named probe.

**When to skip.** If hybrid + rerank already saturate multihop recall
(roughly 0.95+ on the slice), the graph build cannot show a delta worth
its cost. Check the Upgrade A/B results before committing to D.

---

## 6. Status corrections to the original future-work list

- **Second RAGAS judge: already shipped.** The May 28 run uses DeepSeek
  v4 Flash as a cross-provider judge, and the README documents the
  self-bias delta (context_precision -0.18 under the honest judge). Stop
  listing it as future work. Present it as a completed experiment; it is
  one of the strongest results in the repo.
- **Answer cache: not "enable", build.** Only `answer_cache_ttl` exists
  in settings; there is no implementation. Small task when needed: key =
  hash of (question, document_id, top_k, retrieval_mode, prompt/model
  version), invalidate per document on re-ingest, and make eval runs
  bypass it so experiments never read stale answers.
- **Streaming, per-tenant API keys, rate limits** are real production
  work, but orthogonal to retrieval quality: they produce no eval delta.
  Keep them on a separate "service track" so the retrieval experiment
  story stays clean.

---

## 7. Recommended order

| # | Upgrade | Effort | Evidence it produces | Risk |
|---|---|---|---|---|
| 1 | Reranking (A) | 1-2 days | context_precision up, q050 closed, honest latency cost | low, smallest blast radius |
| 2 | Hybrid BM25 (B) | 2-3 days | 3-way ablation table (dense/sparse/hybrid) | low to medium, index lifecycle discipline |
| 3 | Query rewriting (C) | ~1 day on top of B | multihop up or a documented drift trade-off | medium, can regress factual slice |
| 4 | GraphRAG (D) | 4-7 days | graph-vs-vector multihop comparison | high, most work, gated on remaining headroom |

End-state pipeline (every bracketed stage individually flag-controlled,
each flag's value recorded in every eval report):

```
question
   │
[query rewrite: off | multi | hyde]
   │
retrieve (mode: dense | sparse | hybrid | graph)   fetch_k
   │
[cross-encoder rerank]                             keep top_k
   │
generate (unchanged)
   │
answer + citations + latency + cost
```

---

## 8. Constraints to design around

- **Free-tier quotas:** one full eval run per day; smoke-test with
  `--limit` before spending it. GraphRAG ingest needs the Redis extraction
  cache to be re-runnable at all.
- **HF Space (CPU, ~30 s cold start):** a local cross-encoder grows the
  image and the cold start, so keep the reranker provider-switchable: the
  Space can run hosted while eval runs local.
- **Per-document collections:** every new artifact (sparse index, graph
  store) is per-document and follows the same delete-and-rebuild-on-ingest
  lifecycle; rebuild them together or inherit the staleness bug class.
- **The regression gate stays green the whole time:** flags default off
  until the day's eval run justifies flipping a default. That is the whole
  point of evaluation-as-CI.
