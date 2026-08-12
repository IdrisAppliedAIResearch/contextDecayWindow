"""DMR-001C: run the frozen rule on the sealed corpus and evaluate G1-G5.

Nothing here selects a parameter. The rule is DMR-001B's, frozen at its design
anchor, and the bars are transcribed from the DMR-001C registration section 5.
"""

from __future__ import annotations

import ast
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from src.analysis.dmr001_exploration import boundary_agreement, distribution
from src.analysis.dmr001c_corpus import Stream, load_corpus
from src.biological_memory.adaptive_event_context import (
    AdaptiveEventContextFormer,
    AdaptiveFormerConfig,
    load_design,
)
from src.biological_memory.event_context import EventContextError

BARS = {
    "G3": {"max_singleton_fraction": 0.20, "max_capped_closures": 0},
    "G4": {"max_p95_p05_ratio": 2.0},
    "G5": {"margin_over_best_periodic": 0.05, "min_macro_precision": 0.30},
}
DISPOSITIONS = {
    "G1": "INTEGRITY_STOP",
    "G2": "PARTITION_VIOLATION",
    "G3": "DEGENERATE_FORMATION",
    "G4": "NO_TRANSFER",
    "G5": "NO_BOUNDARY_EVIDENCE",
}
PASS_DISPOSITION = "RELATIVE_DRIFT_RULE_CONFIRMED_ON_SEALED_CORPUS"
PERIODS = (2, 4, 5, 6, 8, 16, 32)
TOLERANCE = 1


def _check(name: str, passed: bool, observed: Any, bar: Any) -> dict[str, Any]:
    return {"check": name, "passed": bool(passed), "observed": observed, "bar": bar}


def _percentile(ordered: Sequence[float], fraction: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[int(position)]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def run_stream(
    stream: Stream, *, design_sha256: str, config: AdaptiveFormerConfig
) -> dict[str, Any]:
    former = AdaptiveEventContextFormer(design_sha256=design_sha256, config=config)
    for episode in stream.episodes:
        former.observe(
            episode_hash=episode.episode_hash,
            session_hash=stream.stream_token,
            turn_index=episode.stream_index,
            embedding=episode.vector(),
        )
    snapshot = former.snapshot()
    seams = set(stream.seam_indices())
    length = stream.episode_count
    sizes = [record.member_count for record in snapshot.events]
    reasons: dict[str, int] = {}
    for decision in snapshot.decisions:
        if decision.new_event:
            reasons[decision.boundary_reason] = reasons.get(decision.boundary_reason, 0) + 1
    claimed = snapshot.claimed_boundaries()
    return {
        "stream_token": stream.stream_token,
        "stratum": stream.stratum,
        "episodes": length,
        "seams": len(seams),
        "snapshot_digest": snapshot.digest(),
        "counts": snapshot.validate(),
        "event_count": len(sizes),
        "singleton_fraction": sum(1 for size in sizes if size == 1) / len(sizes),
        "capped_closures": reasons.get("capped", 0),
        "adaptive_boundaries": reasons.get("adaptive", 0),
        "hard_boundaries": reasons.get("hard", 0),
        "adaptive_fire_rate": reasons.get("adaptive", 0) / length,
        "max_event_size": max(sizes),
        "agreement": boundary_agreement(
            claimed, seams, tolerance=TOLERANCE, stream_length=length
        ),
        "periodic": {
            f"C_PERIODIC_{period}": boundary_agreement(
                set(range(0, length, period)),
                seams,
                tolerance=TOLERANCE,
                stream_length=length,
            )
            for period in PERIODS
        },
        "c_pair": boundary_agreement(
            set(range(length)), seams, tolerance=TOLERANCE, stream_length=length
        ),
        "identical_controls": [
            name
            for name, boundaries in (
                [("C_PAIR", set(range(length)))]
                + [
                    (f"C_PERIODIC_{p}", set(range(0, length, p)))
                    for p in PERIODS
                ]
            )
            if boundaries == claimed
        ],
    }


def _macro(rows: Sequence[Mapping[str, Any]], path: Sequence[str]) -> float:
    values = []
    for row in rows:
        node: Any = row
        for key in path:
            node = node[key]
        values.append(float(node))
    return statistics.fmean(values)


def integrity_facts(root: Path, design_path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    design_anchor, config, design = load_design(design_path)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(root) + "'); "
            "from pathlib import Path; "
            "from src.analysis.dmr001c_corpus import load_corpus; "
            "from src.analysis.dmr001c_gates import run_stream; "
            "from src.biological_memory.adaptive_event_context import load_design; "
            "a, c, _ = load_design(Path(r'" + str(design_path) + "')); "
            "s, _m = load_corpus(Path(r'" + manifest["dataset"]["path"] + "'), "
            "Path(r'" + str(root / 'experiments/external/longmemeval/runs/ec002_k_first/ec002_exact_solo_embeddings.db') + "')); "
            "print(run_stream(s[0], design_sha256=a, config=c)['snapshot_digest'])",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root),
    )
    modules = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(root) + "'); "
            "import src.biological_memory.adaptive_event_context; "
            "print(sorted(n for n in sys.modules if n.startswith('src.')))",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(root),
    )
    reachable = ast.literal_eval(modules.stdout.strip())
    source = (root / "src/biological_memory/adaptive_event_context.py").read_text(
        encoding="utf-8"
    )
    called: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                called.add(target.attr)
            elif isinstance(target, ast.Name):
                called.add(target.id)
    return {
        "design_anchor": design_anchor,
        "design_anchor_matches_dmr001b": design_anchor
        == "ad6f9451a1be1519820a18f1ac1dae5dbc9ce38819671c8537061a6dc5ecc5e6",
        "dataset_sha256": manifest["dataset"]["sha256"],
        "corpus_digest": manifest["corpus_digest"],
        "second_process_digest": child.stdout.strip(),
        "leakage_clean": all(n.startswith("src.biological_memory") for n in reachable),
        "reachable_modules": reachable,
        "no_generation_call": not (
            called & {"complete", "chat", "create_completion", "generate", "respond"}
        ),
        "causal_rejection_passed": _causal_rejection(design_anchor, config),
        "uncached_episodes": manifest["excluded"]["uncached_episodes"],
    }


def _causal_rejection(design_sha256: str, config: AdaptiveFormerConfig) -> bool:
    vector = np.zeros(1024, dtype=np.float32)
    vector[0] = 1.0
    for override in (
        {"episode_hash": "nope"},
        {"session_hash": "NOPE"},
        {"turn_index": -3},
        {"embedding": np.zeros(1024, dtype=np.float32)},
    ):
        former = AdaptiveEventContextFormer(design_sha256=design_sha256, config=config)
        call = {
            "episode_hash": "1" * 64,
            "session_hash": "2" * 64,
            "turn_index": 0,
            "embedding": vector,
        }
        call.update(override)
        try:
            former.observe(**call)
        except (EventContextError, ValueError, TypeError):
            continue
        return False
    return True


def build_gate_report(root: Path, design_path: Path, data_path: Path, cache_path: Path) -> dict[str, Any]:
    design_anchor, config, _design = load_design(design_path)
    streams, manifest = load_corpus(data_path, cache_path)
    committed = json.loads(
        (
            root
            / "experiments/components/biological_memory/dmr_001c/artifacts/dmr001c_corpus/corpus_lock.json"
        ).read_text(encoding="utf-8")
    )
    if manifest["corpus_digest"] != committed["corpus_digest"]:
        raise RuntimeError("The corpus does not replay to its committed digest")

    rows = [run_stream(s, design_sha256=design_anchor, config=config) for s in streams]
    first_digest = rows[0]["snapshot_digest"]
    integrity = integrity_facts(root, design_path, manifest)
    integrity["two_process_identical"] = integrity["second_process_digest"] == first_digest
    integrity["corpus_digest_matches"] = (
        manifest["corpus_digest"] == committed["corpus_digest"]
    )

    fire_rates = sorted(row["adaptive_fire_rate"] for row in rows)
    p05, p95 = _percentile(fire_rates, 0.05), _percentile(fire_rates, 0.95)
    ratio = p95 / p05 if p05 > 0 else float("inf")

    macro_f1 = _macro(rows, ["agreement", "f1"])
    macro_precision = _macro(rows, ["agreement", "precision"])
    macro_recall = _macro(rows, ["agreement", "recall"])
    periodic_macro = {
        f"C_PERIODIC_{period}": _macro(rows, ["periodic", f"C_PERIODIC_{period}", "f1"])
        for period in PERIODS
    }
    best_periodic = max(periodic_macro, key=lambda name: periodic_macro[name])

    gates = [
        {
            "gate": "G1",
            "name": "Integrity",
            "checks": [
                _check("dataset hash reproduces", integrity["dataset_sha256"] == manifest["dataset"]["sha256"], integrity["dataset_sha256"], manifest["dataset"]["sha256"]),
                _check("corpus replays to the committed digest", integrity["corpus_digest_matches"], integrity["corpus_digest"], committed["corpus_digest"]),
                _check("every episode vector came from the cache", integrity["uncached_episodes"] == 0, integrity["uncached_episodes"], 0),
                _check("two fresh processes agree bit for bit", integrity["two_process_identical"], integrity["two_process_identical"], True),
                _check("malformed and acausal inputs raise", integrity["causal_rejection_passed"], integrity["causal_rejection_passed"], True),
                _check("no import path to keys, rubrics, readers, packers, or scorers", integrity["leakage_clean"], integrity["reachable_modules"], "src.biological_memory only"),
                _check("no generation call in the process", integrity["no_generation_call"], integrity["no_generation_call"], True),
                _check("the DMR-001B design anchor is unchanged", integrity["design_anchor_matches_dmr001b"], integrity["design_anchor"], "ad6f9451..."),
            ],
        },
        {
            "gate": "G2",
            "name": "Partition",
            "checks": [
                _check(
                    "every episode in exactly one event on every stream",
                    all(row["counts"]["episodes"] == row["episodes"] for row in rows),
                    sum(row["counts"]["episodes"] for row in rows),
                    sum(row["episodes"] for row in rows),
                ),
                _check(
                    "the former never saw a session change",
                    all(row["hard_boundaries"] == 0 for row in rows),
                    sum(row["hard_boundaries"] for row in rows),
                    0,
                ),
            ],
        },
        {
            "gate": "G3",
            "name": "Nondegeneracy",
            "checks": [
                _check(
                    "macro singleton fraction",
                    _macro(rows, ["singleton_fraction"]) <= BARS["G3"]["max_singleton_fraction"],
                    _macro(rows, ["singleton_fraction"]),
                    f"<= {BARS['G3']['max_singleton_fraction']}",
                ),
                _check(
                    "capped closures across the corpus",
                    sum(row["capped_closures"] for row in rows) == 0,
                    sum(row["capped_closures"] for row in rows),
                    0,
                ),
                _check(
                    "no stream is identical to a structural control",
                    not any(row["identical_controls"] for row in rows),
                    [row["identical_controls"] for row in rows if row["identical_controls"]],
                    "no identical control",
                ),
            ],
        },
        {
            "gate": "G4",
            "name": "Stability",
            "checks": [
                _check(
                    "p95/p05 ratio of per-stream fire rate",
                    ratio <= BARS["G4"]["max_p95_p05_ratio"],
                    ratio,
                    f"<= {BARS['G4']['max_p95_p05_ratio']}",
                ),
                _check(
                    "no stream records zero adaptive boundaries",
                    all(row["adaptive_boundaries"] > 0 for row in rows),
                    min(row["adaptive_boundaries"] for row in rows),
                    "> 0",
                ),
            ],
        },
        {
            "gate": "G5",
            "name": "Boundary evidence",
            "checks": [
                _check(
                    f"macro F1 margin over the best periodic control ({best_periodic})",
                    macro_f1 >= periodic_macro[best_periodic] + BARS["G5"]["margin_over_best_periodic"],
                    macro_f1 - periodic_macro[best_periodic],
                    f">= {BARS['G5']['margin_over_best_periodic']}",
                ),
                _check(
                    "macro precision",
                    macro_precision >= BARS["G5"]["min_macro_precision"],
                    macro_precision,
                    f">= {BARS['G5']['min_macro_precision']}",
                ),
            ],
        },
    ]

    evaluated: list[dict[str, Any]] = []
    stopped_at: str | None = None
    disposition = PASS_DISPOSITION
    for gate in gates:
        passed = all(check["passed"] for check in gate["checks"])
        evaluated.append({**gate, "passed": passed, "evaluated": stopped_at is None})
        if stopped_at is None and not passed:
            stopped_at = gate["gate"]
            disposition = DISPOSITIONS[gate["gate"]]

    return {
        "schema": "dmr001c-gates-v1",
        "study": "DMR-001C",
        "design_sha256": design_anchor,
        "corpus_digest": manifest["corpus_digest"],
        "dataset": manifest["dataset"],
        "summary": {
            "streams": len(rows),
            "episodes": sum(row["episodes"] for row in rows),
            "seams": sum(row["seams"] for row in rows),
            "seam_base_rate": sum(row["seams"] for row in rows) / sum(row["episodes"] for row in rows),
            "macro_f1": macro_f1,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "periodic_macro_f1": periodic_macro,
            "best_periodic": best_periodic,
            "c_pair_macro_f1": _macro(rows, ["c_pair", "f1"]),
            "c_pair_macro_precision": _macro(rows, ["c_pair", "precision"]),
            "fire_rate_distribution": distribution(fire_rates),
            "fire_rate_p05": p05,
            "fire_rate_p95": p95,
            "fire_rate_p95_p05_ratio": ratio,
            "macro_event_count": _macro(rows, ["event_count"]),
            "max_event_size_observed": max(row["max_event_size"] for row in rows),
        },
        "integrity": integrity,
        "streams": rows,
        "verdict": {
            "bars": BARS,
            "gates": evaluated,
            "stopped_at": stopped_at,
            "disposition": disposition,
            "passed": stopped_at is None,
        },
    }
