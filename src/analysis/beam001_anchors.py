"""Binding committed-mechanism anchors for BEAM-001 Part 1."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import spacy

from analysis.beam001_parent_opportunity import _admit_opportunities
from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT, build_episodes
from analysis.tc008_study import load_blind_manifest, load_blind_vectors
from analysis.tc009_dependency_graph_probe import BLIND
from analysis.tc010_study import CONVEX_SELECTIONS
from analysis.tc011_spread import extract_facets, facet_idf
from analysis.tc011_study import _initial_indices, _score_vector
from analysis.tc013_fanout import fanout_aspect, weighted_facet_overlap

ROOT = REPO_ROOT / "experiments/comparisons/beam_001"
OUTPUT = ROOT / "artifacts/anchors/reproduction.json"
CC007_ROOT = REPO_ROOT / "experiments/components/episodic_chat/artifacts/cc007"
TC014_ROOT = REPO_ROOT / "experiments/components/tier_cost/artifacts/tc014/preflight"

PACKAGE_TREE = "ae3058f072a9c5b8ce59b130066db11a977e7ab1"
ARTIFACT_HASHES = {
    CC007_ROOT / "preflight.json": "78e5536e875df79b106a78f2fdc2899964653c300b3bda1ce7355be7ce43e184",
    CC007_ROOT / "activation.json": "f57d6a14e5bd52b0754457785e290fe326d72a4a41755c44484a852b7562faf6",
    TC014_ROOT / "preflight.json": "9ba1e5d0f13365773a9c3ab7ab6d5f21807538f62268a0cf0fa4c56f02154ae7",
    TC014_ROOT / "selections.jsonl.gz": "32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7",
}
EXPECTED_TC014_ROWS = 871
SELECTOR_SHA256 = "2b1f209051a2a6a51f1afb4584b7e16e5c34b0535adacd7532935b18014b7698"


class BeamAnchorError(RuntimeError):
    pass


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _verify_artifacts() -> dict[str, Any]:
    observed = {}
    for path, expected in ARTIFACT_HASHES.items():
        actual = sha256_file(path)
        if actual != expected:
            raise BeamAnchorError(f"Committed anchor drifted: {path}")
        observed[path.relative_to(REPO_ROOT).as_posix()] = actual
    cc007 = json.loads((CC007_ROOT / "preflight.json").read_text(encoding="utf-8"))
    activation = json.loads((CC007_ROOT / "activation.json").read_text(encoding="utf-8"))
    tc014 = json.loads((TC014_ROOT / "preflight.json").read_text(encoding="utf-8"))
    if (
        cc007.get("status") != "PASS"
        or cc007["pf6"].get("mismatches") != 0
        or activation.get("status") != "PASS"
        or activation.get("mismatches") != 0
        or tc014.get("status") != "PASS"
        or tc014["pf6"].get("controls") != 3_484
    ):
        raise BeamAnchorError("A committed reproduction gate is not passing")
    return observed


def _verify_package_tree() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD:episodic"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    observed = result.stdout.strip()
    if observed != PACKAGE_TREE:
        raise BeamAnchorError(f"episodic package tree drifted: {observed}")
    return observed


def _verify_tc014_port() -> dict[str, Any]:
    cases = load_blind_manifest(BLIND)
    vectors, reuse = load_blind_vectors(cases)
    nlp = spacy.load("en_core_web_sm")
    prepared: dict[str, tuple[Any, ...]] = {}
    for case in cases:
        episodes = build_episodes(case, vectors)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        facets = tuple(extract_facets(doc) for doc in docs)
        idf, _ = facet_idf(facets)
        facet_weight, overlap = weighted_facet_overlap(facets, idf)
        prepared[case.sample_id] = (episodes, facet_weight, overlap)

    expected_rows = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _load_rows(TC014_ROOT / "selections.jsonl.gz")
    }
    sources = _load_rows(CONVEX_SELECTIONS)
    mismatches: list[dict[str, Any]] = []
    checked = 0
    for source in sources:
        episodes, facet_weight, overlap = prepared[source["sample_id"]]
        by_id = {episode.identity: index for index, episode in enumerate(episodes)}
        relevance = tuple(by_id[value] for value in source["arms"]["cc80"]["order"])
        scores = _score_vector(source, relevance, len(episodes))
        parents = _initial_indices(episodes, relevance, 32_000)
        fanout = fanout_aspect(
            episodes,
            np.asarray(facet_weight, dtype=np.float64),
            np.asarray(overlap, dtype=np.float64),
            scores,
            relevance,
            parents,
            16_000,
        )
        allocation, _trace = _admit_opportunities(
            episodes,
            relevance,
            fanout,
            np.asarray(scores, dtype=np.float64),
            np.asarray(facet_weight, dtype=np.float64),
            32_000,
        )
        expected = expected_rows[
            (source["sample_id"], int(source["source_index"]))
        ]["budgets"]["32000"]["opportunity"]
        if (
            list(allocation.selected_ids) != expected["selected_ids"]
            or allocation.payload_sha256 != expected["payload_sha256"]
        ):
            mismatches.append(
                {
                    "sample_id": source["sample_id"],
                    "source_index": source["source_index"],
                }
            )
        checked += 1
    if checked != EXPECTED_TC014_ROWS or mismatches:
        raise BeamAnchorError(
            f"TC-014 port mismatch: checked={checked}, mismatches={len(mismatches)}"
        )
    return {
        "checked": checked,
        "mismatches": 0,
        "cache_hits": reuse["hits"],
        "cache_misses": reuse["misses"],
    }


def run(output: Path = OUTPUT) -> dict[str, Any]:
    selector_path = REPO_ROOT / "src/analysis/beam001_parent_opportunity.py"
    if sha256_file(selector_path) != SELECTOR_SHA256:
        raise BeamAnchorError("BEAM-001 selector source drifted before replay")
    result = {
        "schema": "beam001-reproduction-v1",
        "status": "PASS",
        "package_tree": _verify_package_tree(),
        "selector_sha256": SELECTOR_SHA256,
        "artifact_hashes": _verify_artifacts(),
        "tc014_opportunity": _verify_tc014_port(),
        "controls": {
            "cc007_trace_groups": 4_355,
            "cc007_activation_payloads": 871,
        },
        "calls": {"embedding_model": 0, "llm_or_generative": 0},
        "outcomes_opened": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    output.write_text(raw, encoding="utf-8")
    result["artifact_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
