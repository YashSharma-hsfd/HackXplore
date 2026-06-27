"""Knowledge-graph layer (Graph-lite) — networkx serialized to disk.

Two node kinds:
  - "entity": a thing (engine, part, fuel, symptom). id = ``ent::<name>``.
  - "spec":   a canonical structured fact (subject + attribute = value + unit).
              id = ``spec::<subject>::<attribute>``. This is the EDITABLE node —
              `update_fact` changes its value once and flags it `curated:true`.

Edges (MultiDiGraph): entity →(attribute)→ spec ("has_spec"), and
entity →(relation)→ entity ("relation"). Every node/edge carries the `source`
chunk id so a chunk edit can re-extract just its triples.

The `curated:true` guard (CLAUDE.md §5): re-extraction never overwrites a node a
human has edited. Persistence is a plain nodes/edges JSON dict (version-robust,
and doubles as the /graph viz payload).
"""

from __future__ import annotations

import json
import logging
import os
import threading

import networkx as nx

from rag_service.config import settings

logger = logging.getLogger(__name__)

_lock = threading.RLock()
_graph: nx.MultiDiGraph | None = None


def _norm(s) -> str:
    return " ".join(str(s).strip().split())


def _key(s) -> str:
    return _norm(s).lower()


def _entity_id(name) -> str:
    return f"ent::{_key(name)}"


def _spec_id(subject, attribute) -> str:
    return f"spec::{_key(subject)}::{_key(attribute) or 'value'}"


def _serialize(g: nx.MultiDiGraph) -> dict:
    # Structural keys are underscored so they can't collide with edge/node data
    # attributes (edges carry their own `source` = chunk id; a plain "source"
    # structural key would be overwritten by it on round-trip).
    return {
        "nodes": [{"_id": n, **d} for n, d in g.nodes(data=True)],
        "edges": [
            {"_from": u, "_to": v, "_key": k, **d}
            for u, v, k, d in g.edges(keys=True, data=True)
        ],
    }


def _deserialize(data: dict) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for nd in data.get("nodes", []):
        nd = dict(nd)
        g.add_node(nd.pop("_id"), **nd)
    for e in data.get("edges", []):
        e = dict(e)
        u, v, k = e.pop("_from"), e.pop("_to"), e.pop("_key", None)
        g.add_edge(u, v, key=k, **e)
    return g


def get_graph() -> nx.MultiDiGraph:
    global _graph
    with _lock:
        if _graph is None:
            if os.path.exists(settings.graph_store_path):
                with open(settings.graph_store_path, encoding="utf-8") as f:
                    _graph = _deserialize(json.load(f))
            else:
                _graph = nx.MultiDiGraph()
        return _graph


def save() -> None:
    with _lock:
        g = get_graph()
        os.makedirs(os.path.dirname(settings.graph_store_path) or ".", exist_ok=True)
        with open(settings.graph_store_path, "w", encoding="utf-8") as f:
            json.dump(_serialize(g), f, ensure_ascii=False, indent=2)


def invalidate() -> None:
    """Drop the in-memory graph so the next access reloads from disk."""
    global _graph
    with _lock:
        _graph = None


def add_extraction(
    chunk_id: str, source: str, specs: list[dict], relations: list[dict], persist: bool = True
) -> None:
    """Merge one chunk's spec + relation triples into the graph.

    Skips any spec node already flagged ``curated:true`` (manual edits win).
    """
    with _lock:
        g = get_graph()
        for s in specs:
            subj, attr = _norm(s.get("subject", "")), _norm(s.get("attribute", ""))
            val, unit = _norm(s.get("value", "")), _norm(s.get("unit", ""))
            if not subj or not val:
                continue
            sid = _spec_id(subj, attr)
            if g.has_node(sid) and g.nodes[sid].get("curated"):
                continue  # curated guard
            ent = _entity_id(subj)
            if not g.has_node(ent):
                g.add_node(ent, label=subj, kind="entity")
            g.add_node(
                sid,
                label=f"{attr}: {val} {unit}".strip(),
                kind="spec",
                subject=subj,
                attribute=attr,
                value=val,
                unit=unit,
                source=chunk_id,
                source_doc=source,
                curated=False,
            )
            g.add_edge(ent, sid, key=attr or "value", rel=attr or "value", kind="has_spec", source=chunk_id)
        for r in relations:
            subj, rel, obj = _norm(r.get("subject", "")), _norm(r.get("relation", "")), _norm(r.get("object", ""))
            if not subj or not obj:
                continue
            a, b = _entity_id(subj), _entity_id(obj)
            if not g.has_node(a):
                g.add_node(a, label=subj, kind="entity")
            if not g.has_node(b):
                g.add_node(b, label=obj, kind="entity")
            g.add_edge(a, b, key=rel or "related", rel=rel or "related", kind="relation", source=chunk_id)
        if persist:
            save()


def remove_chunk(chunk_id: str, persist: bool = True) -> None:
    """Drop a chunk's non-curated triples (used before re-extracting on an edit)."""
    with _lock:
        g = get_graph()
        edges = [(u, v, k) for u, v, k, d in g.edges(keys=True, data=True) if d.get("source") == chunk_id]
        g.remove_edges_from(edges)
        specs = [
            n
            for n, d in list(g.nodes(data=True))
            if d.get("kind") == "spec" and d.get("source") == chunk_id and not d.get("curated")
        ]
        g.remove_nodes_from(specs)
        orphans = [n for n in list(g.nodes()) if g.degree(n) == 0]
        g.remove_nodes_from(orphans)
        if persist:
            save()


def update_fact(spec_id: str, new_value: str, persist: bool = True) -> dict:
    """Edit a structured fact in one shot and flag it curated (the §5 edit feature)."""
    with _lock:
        g = get_graph()
        if not g.has_node(spec_id):
            raise KeyError(spec_id)
        nd = g.nodes[spec_id]
        nd["value"] = _norm(new_value)
        nd["curated"] = True
        nd["label"] = f"{nd.get('attribute', '')}: {nd['value']} {nd.get('unit', '')}".strip()
        if persist:
            save()
        return {"id": spec_id, **nd}


def neighbors(name: str, depth: int = 1) -> list[dict]:
    """Entities/specs connected to `name` — backs the /related recommender."""
    g = get_graph()
    start = _entity_id(name)
    if not g.has_node(start):
        return []
    und = g.to_undirected(as_view=True)
    seen, frontier = {start}, [start]
    for _ in range(max(1, depth)):
        nxt = []
        for n in frontier:
            for m in und.neighbors(n):
                if m not in seen:
                    seen.add(m)
                    nxt.append(m)
        frontier = nxt
    seen.discard(start)
    return [{"id": n, **g.nodes[n]} for n in seen]


def find_specs(text: str) -> list[dict]:
    """Spec nodes whose subject/attribute appears in `text` — answer-time exact facts."""
    g = get_graph()
    t = text.lower()
    out = []
    for n, d in g.nodes(data=True):
        if d.get("kind") != "spec":
            continue
        if _key(d.get("subject", "")) in t or (d.get("attribute") and _key(d.get("attribute", "")) in t):
            out.append({"id": n, **d})
    return out


def to_vis() -> dict:
    """nodes/edges payload for the vis.js graph panel (the /graph endpoint)."""
    g = get_graph()
    nodes = [
        {
            "id": n,
            "label": d.get("label", n),
            "group": d.get("kind", "entity"),
            "curated": bool(d.get("curated", False)),
        }
        for n, d in g.nodes(data=True)
    ]
    edges = [{"from": u, "to": v, "label": d.get("rel", "")} for u, v, d in g.edges(data=True)]
    return {"nodes": nodes, "edges": edges}


def stats() -> dict:
    g = get_graph()
    return {
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "specs": sum(1 for _, d in g.nodes(data=True) if d.get("kind") == "spec"),
    }
