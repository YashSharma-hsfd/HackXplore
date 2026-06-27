"""Day 10-11: RAGAS evaluation harness for the RAG service.

Ingests the eval corpus into a single Chroma collection, runs every question in
eval/dataset.jsonl through retrieve + generate, scores the answers with RAGAS,
and writes a timestamped JSON/CSV pair plus a Markdown summary to eval/results/.

    uv run python eval/run_ragas.py                # full run over dataset.jsonl
    uv run python eval/run_ragas.py --limit 3      # quick smoke test
    uv run python eval/run_ragas.py --rebuild      # re-ingest the corpus first
    uv run python eval/run_ragas.py --top-k 5      # override retrieval depth

--rebuild is required after changing chunk_size (the corpus must be re-chunked);
changing --top-k alone does not need a rebuild.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb
import ragas_eval
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from rag_service.config import settings
from rag_service.core import graph
from rag_service.core.generation import generate
from rag_service.core.retrieval import retrieve
from rag_service.llm.openai_client import setup_llamaindex_settings

EVAL_DIR = Path(__file__).resolve().parent
CORPUS_DIR = EVAL_DIR / "corpus"
RESULTS_DIR = EVAL_DIR / "results"
DATASET_PATH = EVAL_DIR / "dataset.jsonl"

# Every corpus PDF shares one collection so retrieval searches the whole corpus,
# and adversarial questions (source_doc=null) still have something to retrieve.
CORPUS_DOC_ID = "eval_corpus"

# Substrings that mark a correct refusal — must track generation.py's prompt.
# Bilingual: the model refuses in the question's language (EN or DE), so a
# German refusal ("Ich habe nicht genügend Informationen.") must count too.
_REFUSAL_MARKERS = (
    "don't have enough information",
    "do not have enough information",
    "nicht genügend informationen",
    "nicht genug informationen",
)


def load_dataset(limit: int | None) -> list[dict]:
    lines = DATASET_PATH.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    return rows[:limit] if limit else rows


def ensure_corpus_ingested(rebuild: bool) -> None:
    """Verify the live corpus collection is populated.

    We eval the REAL system: the engine corpus is already in
    ``settings.collection_name`` (ingested via the app), so this checks it isn't
    empty rather than re-ingesting anything. ``rebuild`` is accepted for CLI
    compatibility but unused — re-ingest via the app / ingest script instead.
    """
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    try:
        n = client.get_collection(settings.collection_name).count()
    except Exception:
        n = 0
    if n == 0:
        raise SystemExit(
            f"corpus '{settings.collection_name}' is empty — ingest the Data/ "
            "documents first (POST /ingest or the ingest script)."
        )
    print(f"eval against live corpus '{settings.collection_name}' ({n} chunks)")


def answer_question(question: str, top_k: int) -> tuple[str, list[str]]:
    """Retrieve + generate with production parity: hybrid retrieval + graph facts."""
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            nodes = retrieve(question, top_k)
            contexts = [n.node.get_content() for n in nodes]
            facts = graph.find_specs(question)[:12]
            if facts:
                contexts.append(
                    "KNOWN FACTS:\n"
                    + "\n".join(
                        f"- {f.get('subject', '')} {f.get('attribute', '')}: "
                        f"{f.get('value', '')} {f.get('unit', '')}".strip()
                        for f in facts
                    )
                )
            answer = generate(question, nodes, facts=facts).answer
            return answer, contexts
        except Exception as err:
            last_err = err
            wait = 30 * (attempt + 1)
            print(f"    pipeline error (attempt {attempt + 1}/3): {err} — retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"pipeline failed after 3 attempts: {last_err}")


def _is_refusal(answer: str) -> bool:
    low = answer.lower()
    return any(marker in low for marker in _REFUSAL_MARKERS)


def run_pipeline(rows: list[dict], top_k: int) -> tuple[list[dict], list[dict]]:
    """Run every question through the RAG pipeline.

    Returns (samples, meta): `samples` feed RAGAS, `meta` carries the dataset
    fields the report needs. Both lists stay index-aligned with `rows`.
    """
    samples: list[dict] = []
    meta: list[dict] = []
    for i, row in enumerate(rows, start=1):
        question = row["question"]
        print(f"[{i}/{len(rows)}] {row['id']} ({row['category']}): {question[:64]}")
        try:
            answer, contexts = answer_question(question, top_k)
            error = ""
        except Exception as err:
            answer, contexts, error = "", [], str(err)
            print(f"    FAILED: {err}")

        samples.append(
            {
                "user_input": question,
                # RAGAS needs non-empty fields; placeholders only appear on failure.
                "retrieved_contexts": contexts or ["(no context retrieved)"],
                "response": answer or "(no answer generated)",
                "reference": row["ground_truth_answer"],
            }
        )
        meta.append(
            {
                "id": row["id"],
                "question": question,
                "category": row["category"],
                "difficulty": row["difficulty"],
                "source_doc": row.get("source_doc"),
                "response": answer,
                "n_retrieved": len(contexts),
                "error": error,
                "refused": _is_refusal(answer),
            }
        )
    return samples, meta


def _num(value: Any) -> float | None:
    """Coerce a RAGAS cell to a JSON-safe float; NaN and non-numbers become None."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(num) else round(num, 4)


def _mean(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    return round(sum(nums) / len(nums), 4) if nums else None


def _fmt(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else "—"


def _summarize(per_question: list[dict], metrics: list[str]) -> tuple[dict, dict, float | None, int, int]:
    """Aggregate per-question scores into headline + per-category numbers.

    The four RAG-quality metrics are averaged over ANSWERABLE questions only.
    Adversarial questions (source_doc=null) are *supposed* to be refused, and a
    refusal grounds no claims, so it scores ~0 on faithfulness/relevancy —
    including them would understate retrieval/answer quality. They get their own
    metric instead: the refusal rate.
    """
    answerable = [pq for pq in per_question if pq["source_doc"] is not None]
    adversarial = [pq for pq in per_question if pq["source_doc"] is None]

    aggregate = {name: _mean([pq["scores"][name] for pq in answerable]) for name in metrics}

    by_category: dict[str, dict] = {}
    for cat in sorted({pq["category"] for pq in answerable}):
        in_cat = [pq for pq in answerable if pq["category"] == cat]
        by_category[cat] = {
            "n": len(in_cat),
            **{name: _mean([pq["scores"][name] for pq in in_cat]) for name in metrics},
        }

    refusal_rate = (
        round(sum(pq["refused"] for pq in adversarial) / len(adversarial), 4)
        if adversarial
        else None
    )
    return aggregate, by_category, refusal_rate, len(answerable), len(adversarial)


def build_report(
    meta: list[dict], scores_df: Any, top_k: int, duration_s: float, json_name: str
) -> dict:
    """Merge dataset metadata with RAGAS scores into the report structure."""
    metrics = ragas_eval.METRIC_NAMES
    records = scores_df.to_dict(orient="records")

    per_question: list[dict] = []
    for m, rec in zip(meta, records):
        per_question.append(
            {
                "id": m["id"],
                "category": m["category"],
                "difficulty": m["difficulty"],
                "source_doc": m["source_doc"],
                "question": m["question"],
                "response": m["response"],
                "n_retrieved": m["n_retrieved"],
                "error": m["error"],
                "refused": m["refused"],
                "scores": {name: _num(rec.get(name)) for name in metrics},
            }
        )

    aggregate, by_category, refusal_rate, n_answerable, n_adversarial = _summarize(
        per_question, metrics
    )

    return {
        "run": {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generation_model": settings.llm_model,
            "judge_provider": settings.judge_provider,
            "judge_model": ragas_eval.judge_model(),
            "embed_model": settings.embedding_model,
            "ragas_version": ragas_eval.RAGAS_VERSION,
            "top_k": top_k,
            "chunk_size": settings.chunk_size,
            "n_questions": len(per_question),
            "n_answerable": n_answerable,
            "n_adversarial": n_adversarial,
            "n_errors": sum(1 for pq in per_question if pq["error"]),
            "duration_s": round(duration_s, 1),
            "json_file": json_name,
        },
        "aggregate": aggregate,
        "by_category": by_category,
        "adversarial_refusal_rate": refusal_rate,
        "results": per_question,
    }


def write_csv(path: Path, per_question: list[dict]) -> None:
    metrics = ragas_eval.METRIC_NAMES
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["id", "category", "difficulty", "source_doc", "refused", "error", "n_retrieved"]
            + metrics
            + ["question", "response"]
        )
        for pq in per_question:
            writer.writerow(
                [
                    pq["id"],
                    pq["category"],
                    pq["difficulty"],
                    pq["source_doc"],
                    pq["refused"],
                    pq["error"],
                    pq["n_retrieved"],
                ]
                + [pq["scores"][m] if pq["scores"][m] is not None else "" for m in metrics]
                + [pq["question"], pq["response"]]
            )


def render_markdown(report: dict) -> str:
    run = report["run"]
    metrics = list(report["aggregate"].keys())
    out: list[str] = [
        "# RAGAS Evaluation — latest",
        "",
        f"**Run:** {run['timestamp']}  ",
        f"**Generation:** `{run['generation_model']}` · "
        f"**Judge:** `{run['judge_model']}` · "
        f"**top_k:** {run['top_k']} · **chunk_size:** {run['chunk_size']}  ",
        f"**Questions:** {run['n_questions']} (errors: {run['n_errors']}) · "
        f"**Duration:** {run['duration_s']}s · **RAGAS:** {run['ragas_version']}",
        "",
        "## Aggregate scores",
        "",
        f"_RAG-quality metrics averaged over the {run.get('n_answerable', '?')} answerable "
        f"questions; the {run.get('n_adversarial', '?')} adversarial (unanswerable) questions "
        "are measured by the refusal rate below._",
        "",
        "| Metric | Score |",
        "|---|---|",
    ]
    for name in metrics:
        out.append(f"| {name} | {_fmt(report['aggregate'][name])} |")

    out += ["", "## By category", ""]
    out.append("| Category | n | " + " | ".join(metrics) + " |")
    out.append("|---|---|" + "---|" * len(metrics))
    for cat, row in report["by_category"].items():
        cells = " | ".join(_fmt(row[name]) for name in metrics)
        out.append(f"| {cat} | {row['n']} | {cells} |")
    out.append("")

    rate = report["adversarial_refusal_rate"]
    if rate is not None:
        out.append(
            f"**Adversarial refusal rate:** {_fmt(rate)} "
            f"({run.get('n_adversarial', '?')} questions) — fraction of unanswerable "
            "questions the model correctly declined to answer."
        )
        out.append("")

    out += [
        "## Notes",
        "",
        f"Per-question scores: `{run['json_file']}` (JSON) and the matching `.csv`.",
        "",
    ]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation over eval/dataset.jsonl")
    parser.add_argument("--limit", type=int, default=None, help="run only the first N questions")
    parser.add_argument("--rebuild", action="store_true", help="force corpus re-ingestion")
    parser.add_argument(
        "--top-k",
        type=int,
        default=settings.top_k,
        help="retrieval depth (default: settings.top_k)",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    setup_llamaindex_settings()
    ensure_corpus_ingested(args.rebuild)

    rows = load_dataset(args.limit)
    print(f"\nrunning {len(rows)} question(s) at top_k={args.top_k}\n")

    start = time.perf_counter()
    samples, meta = run_pipeline(rows, args.top_k)
    print(
        f"\nscoring {len(samples)} answer(s) with RAGAS — the judge model is called "
        "many times per question, expect a few minutes ...\n"
    )
    scores_df = ragas_eval.score(samples)
    duration = time.perf_counter() - start

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_name = f"ragas_{stamp}.json"
    report = build_report(meta, scores_df, args.top_k, duration, json_name)

    json_path = RESULTS_DIR / json_name
    csv_path = RESULTS_DIR / f"ragas_{stamp}.csv"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_csv(csv_path, report["results"])
    (RESULTS_DIR / "latest.md").write_text(render_markdown(report), encoding="utf-8")

    print("\n=== RAGAS evaluation complete ===")
    for name, value in report["aggregate"].items():
        print(f"  {name:<40} {_fmt(value)}")
    if report["adversarial_refusal_rate"] is not None:
        print(f"  {'adversarial refusal rate':<40} {_fmt(report['adversarial_refusal_rate'])}")
    print(f"\n  errors: {report['run']['n_errors']}/{report['run']['n_questions']}")
    print(f"  results: {json_path.name}, {csv_path.name}, latest.md")


if __name__ == "__main__":
    main()
