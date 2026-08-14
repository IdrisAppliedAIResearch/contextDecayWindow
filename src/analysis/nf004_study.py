"""Ordered execution gates and sealed measurement stages for NF-004."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from analysis.nf004_measurement import (
    BUDGET,
    DEVELOPMENT_IDS,
    HOLDOUT_IDS,
    SECONDARY_BUDGET,
    adapt_split,
    canonical_bytes,
    canonical_digest,
    distribution,
    paired_counts,
    run_measurement,
    sha256_file,
    vector_texts,
)
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRATION = Path(
    "experiments/components/biological_memory/nf_004/NF_004_PRE_REGISTRATION.md"
)
REGISTRATION_COMMIT = "95f0d25c8e898998dcbf0c8b95d370896c57c929"
REGISTRATION_LF_SHA256 = (
    "de2d5e05646b769cac8a86a64443062a51024edea44af4a6a951a42d1a8c213d"
)
SOURCE_MANIFEST = Path("experiments/external/locomo/artifacts/source_manifest.json")
SOURCE_MANIFEST_SHA256 = (
    "58958407a451eed0e6031f643234c73fe9026a9ceca5b56ed7a4f500af8b3693"
)
HOLDOUT_INVENTORY = Path(
    "experiments/external/locomo/artifacts/holdout_inventory.json"
)
HOLDOUT_INVENTORY_SHA256 = (
    "cde6e37ad046198f9b9326497c9d13db4c906fb02026df16243afede2b820789"
)
DEVELOPMENT_MANIFEST = Path(
    "experiments/external/locomo/artifacts/development_vector_manifest.json"
)
DEVELOPMENT_MANIFEST_SHA256 = (
    "6f939ed9da7aa4fff44f72aaa3585c863ce7a15d061eecd96a322a104ed755e1"
)
DEVELOPMENT_CONTROL = Path(
    "experiments/external/locomo/artifacts/ranking_budget_controls.json"
)
DEVELOPMENT_CONTROL_SHA256 = (
    "8ff8bd529f1af00331147b345915dc128ef45acf6c633d04be9d0f9243a79e3b"
)
HOLDOUT_VECTOR_MANIFEST = Path(
    "experiments/components/biological_memory/nf_004/artifacts/"
    "holdout_vector_manifest.json"
)
PREFLIGHT_ARTIFACT = Path(
    "experiments/components/biological_memory/nf_004/artifacts/preflight_g0_g5.json"
)
G6_ARTIFACT = Path(
    "experiments/components/biological_memory/nf_004/artifacts/"
    "g6_holdout_outcomes.json"
)
G7_ARTIFACT = Path(
    "experiments/components/biological_memory/nf_004/artifacts/"
    "g7_result_integrity.json"
)
MECHANISM = Path("src/analysis/nf004_mechanism.py")


class NF004GateStop(RuntimeError):
    def __init__(self, gate: str, detail: str) -> None:
        super().__init__(f"{gate} stopped: {detail}")
        self.gate = gate


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(
        ("git", *args), cwd=REPO_ROOT, text=True
    ).strip()


def _first_commit(path: Path) -> str:
    commits = _git(
        "log", "--diff-filter=A", "--format=%H", "--", path.as_posix()
    ).splitlines()
    if len(commits) != 1:
        raise NF004GateStop(
            "G0", f"Expected one add commit for {path}, found {len(commits)}"
        )
    return commits[0]


def _committed_identity(path: Path) -> dict[str, Any]:
    absolute = REPO_ROOT / path
    if not absolute.is_file():
        raise NF004GateStop("INTEGRITY", f"Missing artifact {path}")
    commit = _first_commit(path)
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", commit, "HEAD"),
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    committed = subprocess.check_output(
        ("git", "show", f"{commit}:{path.as_posix()}"), cwd=REPO_ROOT
    )
    current = absolute.read_bytes()
    if committed != current:
        raise NF004GateStop(
            "INTEGRITY", f"{path} differs from its committed artifact"
        )
    return {
        "path": path.as_posix(),
        "first_commit": commit,
        "sha256": hashlib.sha256(current).hexdigest(),
    }


def enforce_gate_order(
    gates: Sequence[tuple[str, Callable[[], dict[str, Any]]]],
    after: Callable[[], Any] | None = None,
) -> tuple[dict[str, Any], Any | None]:
    results: dict[str, Any] = {}
    for name, gate in gates:
        evidence = gate()
        if evidence.get("pass") is not True:
            raise NF004GateStop(name, str(evidence))
        results[name] = evidence
    return results, after() if after is not None else None


def registration_identity() -> dict[str, Any]:
    path = REPO_ROOT / REGISTRATION
    first_commit = _first_commit(REGISTRATION)
    observed_lf = _lf_sha256(path)
    subprocess.run(
        ("git", "merge-base", "--is-ancestor", REGISTRATION_COMMIT, "HEAD"),
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    passed = (
        first_commit == REGISTRATION_COMMIT
        and observed_lf == REGISTRATION_LF_SHA256
    )
    return {
        "pass": passed,
        "path": REGISTRATION.as_posix(),
        "expected_first_commit": REGISTRATION_COMMIT,
        "observed_first_commit": first_commit,
        "expected_lf_sha256": REGISTRATION_LF_SHA256,
        "observed_lf_sha256": observed_lf,
        "corpus_accessed": False,
    }


def source_population(dataset_path: Path) -> dict[str, Any]:
    source_path = REPO_ROOT / SOURCE_MANIFEST
    inventory_path = REPO_ROOT / HOLDOUT_INVENTORY
    source_hash = sha256_file(source_path)
    inventory_hash = sha256_file(inventory_path)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    population = inventory["population"]
    keys = [row["comparison_key"] for row in population]
    counts = inventory["counts"]
    passed = all(
        (
            source_hash == SOURCE_MANIFEST_SHA256,
            inventory_hash == HOLDOUT_INVENTORY_SHA256,
            dataset_path.stat().st_size == 2_805_274,
            sha256_file(dataset_path)
            == "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
            counts["conversations"] == 6,
            counts["source_qa_records"] == 1_104,
            counts["canonical_unique_qa_records"] == 1_104,
            counts["all_evidence_evaluable_unique_records"] == 1_098,
            counts["duplicate_qa_records"] == 0,
            len(keys) == len(set(keys)) == 1_104,
        )
    )
    return {
        "pass": passed,
        "source_manifest_sha256": source_hash,
        "holdout_inventory_sha256": inventory_hash,
        "dataset_sha256": sha256_file(dataset_path),
        "counts": counts,
        "comparison_key_digest": canonical_digest(sorted(keys)),
    }


def _import_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def mechanism_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    imports = _import_names(source)
    allowed_imports = {"__future__", "dataclasses", "typing", "numpy"}
    violations = [
        f"forbidden import:{name}" for name in sorted(imports - allowed_imports)
    ]
    forbidden_names = {
        "answer",
        "answers",
        "category",
        "evidence",
        "evidence_ids",
        "dia_id",
        "dialogue_ids",
    }
    used_names = {
        node.id.casefold() for node in ast.walk(tree) if isinstance(node, ast.Name)
    }
    used_names.update(
        node.attr.casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    )
    violations.extend(
        f"forbidden identifier:{name}"
        for name in sorted(forbidden_names & used_names)
    )
    lowered = source.casefold()
    for token in (
        "q_facts_key",
        "holdout_inventory",
        "nf004_measurement",
        "locomo_nf_development",
    ):
        if token in lowered:
            violations.append(f"forbidden source reference:{token}")
    return violations


def leakage_gate() -> dict[str, Any]:
    source = (REPO_ROOT / MECHANISM).read_text(encoding="utf-8")
    violations = mechanism_violations(source)
    planted = source + "\nfrom analysis.nf004_measurement import adapt_split\n"
    planted_violations = mechanism_violations(planted)
    return {
        "pass": not violations and bool(planted_violations),
        "mechanism_path": MECHANISM.as_posix(),
        "direct_import_graph": sorted(_import_names(source)),
        "violations": violations,
        "planted_forbidden_import_rejected": bool(planted_violations),
        "planted_violations": planted_violations,
        "measurement_module": "analysis.nf004_measurement",
    }


def vector_seal(dataset_path: Path, cache_path: Path) -> dict[str, Any]:
    from episodic import EmbeddingCache

    manifest_path = REPO_ROOT / HOLDOUT_VECTOR_MANIFEST
    if not manifest_path.is_file():
        raise NF004GateStop("G3", "Holdout vector manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = adapt_split(dataset_path, HOLDOUT_IDS)
    texts = vector_texts(records)
    cache_record = manifest["cache"]
    with EmbeddingCache(
        cache_path,
        mode="reuse",
        expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for text in texts:
            cache(text)
        reuse = cache.record()
    passed = all(
        (
            manifest["schema"] == "nf004-holdout-vectors-v1",
            manifest["dataset_sha256"]
            == "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4",
            manifest["holdout_ids"] == sorted(HOLDOUT_IDS),
            manifest["expected_unique_texts"] == len(texts),
            cache_record["entries"] == len(texts),
            cache_record["model_sha256"] == CARRIED_EMBEDDING_SHA256,
            cache_record["call_shape"] == "solo",
            cache_record["dtype"] == "float32",
            cache_record["dimension"] == 1024,
            reuse["hits"] == len(texts),
            reuse["misses"] == 0,
        )
    )
    return {
        "pass": passed,
        "manifest_sha256": sha256_file(manifest_path),
        "unique_texts": len(texts),
        "cache": reuse,
        "embedding_calls": 0,
        "model_generation_calls": 0,
    }


def _arm_hits(rows: Sequence[dict[str, Any]], arm: str) -> int:
    return sum(row["arms"][arm]["all_evidence"] for row in rows)


def _paired_for_arms(
    rows: Sequence[dict[str, Any]], baseline: str, treatment: str
) -> dict[str, int]:
    gains = sum(
        row["arms"][treatment]["all_evidence"]
        and not row["arms"][baseline]["all_evidence"]
        for row in rows
    )
    losses = sum(
        row["arms"][baseline]["all_evidence"]
        and not row["arms"][treatment]["all_evidence"]
        for row in rows
    )
    return {"gains": gains, "losses": losses, "ties": len(rows) - gains - losses}


def development_replay(
    dataset_path: Path, cache_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = REPO_ROOT / DEVELOPMENT_MANIFEST
    control_path = REPO_ROOT / DEVELOPMENT_CONTROL
    if sha256_file(manifest_path) != DEVELOPMENT_MANIFEST_SHA256:
        raise NF004GateStop("G4", "Development vector manifest changed")
    if sha256_file(control_path) != DEVELOPMENT_CONTROL_SHA256:
        raise NF004GateStop("G4", "Development control artifact changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = adapt_split(dataset_path, DEVELOPMENT_IDS)
    replay = run_measurement(
        records, cache_path, manifest, include_secondary=True
    )
    rows = [row for row in replay["rows"] if row["primary_eligible"]]
    expected_old_keys = {
        hashlib.sha256(
            f"{row['comparison_key']}\0{row['duplicate_ordinal']}".encode("utf-8")
        ).hexdigest()
        for row in replay["rows"]
        if row["duplicate_ordinal"] == 0
    }
    control = json.loads(control_path.read_text(encoding="utf-8"))
    observed_old_keys = {
        row["question_id"]
        for row in control["locomo"]["outcomes"]
        if row["budget"] == BUDGET
    }
    summary = {
        "primary_n": len(rows),
        "unique_n": len(expected_old_keys),
        "comparison_key_identity_reproduced": expected_old_keys
        == observed_old_keys,
        "16k": {
            "session_hits": _arm_hits(rows, "S_SESSION_RANK"),
            "pair_hits": _arm_hits(rows, "P_PAIR_RANK"),
            "paired": _paired_for_arms(
                rows, "S_SESSION_RANK", "P_PAIR_RANK"
            ),
        },
        "32k": {
            "session_hits": _arm_hits(rows, "S_SESSION_RANK_32K"),
            "pair_hits": _arm_hits(rows, "P_PAIR_RANK_32K"),
            "paired": _paired_for_arms(
                rows, "S_SESSION_RANK_32K", "P_PAIR_RANK_32K"
            ),
        },
        "row_digest": canonical_digest(replay["rows"]),
        "cache": replay["cache"],
    }
    expected = {
        "primary_n": 868,
        "unique_n": 871,
        "16k": {
            "session_hits": 702,
            "pair_hits": 773,
            "paired": {"gains": 104, "losses": 33, "ties": 731},
        },
        "32k": {
            "session_hits": 773,
            "pair_hits": 826,
            "paired": {"gains": 71, "losses": 18, "ties": 779},
        },
    }
    comparable = {key: summary[key] for key in expected}
    return {
        "pass": comparable == expected
        and summary["comparison_key_identity_reproduced"]
        and replay["embedding_calls"] == 0,
        "expected": expected,
        "observed": summary,
        "embedding_calls": replay["embedding_calls"],
        "model_generation_calls": replay["model_generation_calls"],
    }, replay


def run_preflight(
    dataset_path: Path,
    holdout_cache_path: Path,
    development_cache_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite {output_path}")
    first_replay: dict[str, Any] = {}

    def g4() -> dict[str, Any]:
        result, replay = development_replay(dataset_path, development_cache_path)
        first_replay["payload"] = replay
        return result

    def g5() -> dict[str, Any]:
        _, repeated = development_replay(dataset_path, development_cache_path)
        first = canonical_bytes(first_replay["payload"])
        second = canonical_bytes(repeated)
        return {
            "pass": first == second,
            "first_sha256": hashlib.sha256(first).hexdigest(),
            "second_sha256": hashlib.sha256(second).hexdigest(),
            "bytes": len(first),
        }

    gates, _ = enforce_gate_order(
        (
            ("G0", registration_identity),
            ("G1", lambda: source_population(dataset_path)),
            ("G2", leakage_gate),
            ("G3", lambda: vector_seal(dataset_path, holdout_cache_path)),
            ("G4", g4),
            ("G5", g5),
        )
    )
    checks = {
        "PF1": {
            "pass": gates["G1"]["pass"] and gates["G3"]["pass"],
            "evidence": "G1 source/population and G3 vector seal",
        },
        "PF2": {
            "pass": gates["G2"]["pass"] and gates["G4"]["pass"],
            "evidence": "pure mechanism identity and exact development replay",
        },
        "PF3": {
            "pass": True,
            "evidence": "enforce_gate_order stops before later gates; planted tests cover G0-G5",
        },
        "PF4": {
            "pass": True,
            "evidence": {
                "WORKS": "6 gains, 0 losses reaches p=.015625",
                "CARRIES_SIGNAL": "4 gains, 1 loss reaches p=.1875",
                "NULL": "1 gain, 1 loss reaches p=.75",
            },
        },
        "PF5": {
            "pass": gates["G4"]["observed"][
                "comparison_key_identity_reproduced"
            ],
            "evidence": "canonical content SHA-256 keys reproduce all 871 development identities",
        },
        "PF6": {
            "pass": gates["G4"]["pass"],
            "evidence": gates["G4"]["observed"],
        },
        "PF7": {
            "pass": gates["G5"]["pass"],
            "evidence": "stateless mechanism and byte-identical complete development replay",
        },
        "PF8": {
            "pass": True,
            "evidence": "All 1,098 eligible holdout items are planned; this cannot detect reader correctness or cross-corpus transfer.",
        },
        "PF9": {
            "pass": True,
            "evidence": "Complete evidence can pass while a reader fails; any-evidence and session-touch cannot set disposition.",
        },
        "PF10": {
            "pass": True,
            "evidence": "NF-004 is availability-only and authorizes no live or adoption claim.",
        },
    }
    payload = {
        "schema": "nf004-preflight-g0-g5-v1",
        "status": "PASS",
        "registration_commit": REGISTRATION_COMMIT,
        "registration_lf_sha256": REGISTRATION_LF_SHA256,
        "gates": gates,
        "preflight": checks,
        "holdout_outcomes_computed": False,
        "embedding_calls_during_measurement": 0,
        "model_generation_calls": 0,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(payload))
    return payload


def _require_passing_preflight() -> dict[str, Any]:
    identity = _committed_identity(PREFLIGHT_ARTIFACT)
    payload = json.loads(
        (REPO_ROOT / PREFLIGHT_ARTIFACT).read_text(encoding="utf-8")
    )
    if payload.get("status") != "PASS":
        raise NF004GateStop("G6", "Committed preflight does not pass")
    expected_gates = {f"G{index}" for index in range(6)}
    if set(payload.get("gates", {})) != expected_gates or not all(
        row.get("pass") is True for row in payload["gates"].values()
    ):
        raise NF004GateStop("G6", "Committed G0-G5 evidence is incomplete")
    return identity


def build_g6_payload(
    dataset_path: Path, cache_path: Path
) -> dict[str, Any]:
    preflight = _require_passing_preflight()
    manifest_path = REPO_ROOT / HOLDOUT_VECTOR_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = adapt_split(dataset_path, HOLDOUT_IDS)
    measured = run_measurement(
        records, cache_path, manifest, include_secondary=True
    )
    primary = [row for row in measured["rows"] if row["primary_eligible"]]
    if len(measured["rows"]) != 1_104 or len(primary) != 1_098:
        raise NF004GateStop(
            "G6",
            f"Population changed: {len(measured['rows'])}/{len(primary)}",
        )
    if measured["embedding_calls"] or measured["model_generation_calls"]:
        raise NF004GateStop("G6", "A model or embedding call occurred")
    return {
        "schema": "nf004-g6-holdout-outcomes-v1",
        "status": "G6_SEALED_OUTCOMES",
        "registration_commit": REGISTRATION_COMMIT,
        "preflight": preflight,
        "vector_manifest_sha256": sha256_file(manifest_path),
        "population": {"arm_inputs": len(measured["rows"]), "primary": len(primary)},
        "budget": BUDGET,
        "secondary_budget": SECONDARY_BUDGET,
        "cache": measured["cache"],
        "embedding_calls": measured["embedding_calls"],
        "model_generation_calls": measured["model_generation_calls"],
        "rows": measured["rows"],
    }


def run_g6(dataset_path: Path, cache_path: Path, output_path: Path) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite {output_path}")
    payload = build_g6_payload(dataset_path, cache_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(payload))
    return payload


def _arm_summary(rows: Sequence[dict[str, Any]], arm: str) -> dict[str, Any]:
    return {
        "any_evidence_hits": sum(
            row["arms"][arm]["any_evidence"] for row in rows
        ),
        "all_evidence_hits": sum(
            row["arms"][arm]["all_evidence"] for row in rows
        ),
        "delivered_candidates": distribution(
            row["arms"][arm]["delivered_candidates"] for row in rows
        ),
        "packed_chars": distribution(
            row["arms"][arm]["packed_chars"] for row in rows
        ),
        "best_evidence_rank": distribution(
            row["arms"][arm]["best_evidence_rank"]
            for row in rows
            if row["arms"][arm]["best_evidence_rank"] is not None
        ),
    }


def _group_summary(
    rows: Sequence[dict[str, Any]], field: str
) -> dict[str, Any]:
    return {
        value: {
            "n": len(group),
            "session_hits": _arm_hits(group, "S_SESSION_RANK"),
            "pair_hits": _arm_hits(group, "P_PAIR_RANK"),
            "paired": paired_counts(group),
        }
        for value in sorted({str(row[field]) for row in rows})
        for group in [[row for row in rows if str(row[field]) == value]]
    }


def _disposition(comparison: dict[str, Any]) -> str:
    gains = comparison["gains"]
    losses = comparison["losses"]
    p = comparison["p_one_sided"]
    if gains >= 2 * losses and p <= 0.05:
        return "WORKS"
    if gains > losses and p <= 0.20:
        return "CARRIES_SIGNAL"
    return "NULL"


def run_g7(
    dataset_path: Path, cache_path: Path, output_path: Path
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite {output_path}")
    g6_identity = _committed_identity(G6_ARTIFACT)
    sealed_bytes = (REPO_ROOT / G6_ARTIFACT).read_bytes()
    sealed = json.loads(sealed_bytes)
    replay = build_g6_payload(dataset_path, cache_path)
    replay_bytes = canonical_bytes(replay)
    if sealed_bytes != replay_bytes:
        raise NF004GateStop("G7", "Holdout replay is not byte-identical")
    if sealed["embedding_calls"] or sealed["model_generation_calls"]:
        raise NF004GateStop("G7", "Sealed outcome records a forbidden call")
    rows = [row for row in sealed["rows"] if row["primary_eligible"]]
    comparison = paired_counts(rows)
    disposition = _disposition(comparison)
    arms = {
        arm: _arm_summary(rows, arm)
        for arm in (
            "S_SESSION_RANK",
            "P_PAIR_RANK",
            "SOURCE_ORDER",
            "S_SESSION_RANK_32K",
            "P_PAIR_RANK_32K",
        )
    }
    payload = {
        "schema": "nf004-g7-result-integrity-v1",
        "status": "COMPLETE",
        "disposition": disposition,
        "claim_scope": "complete exact-evidence availability on sealed LoCoMo holdout",
        "registration_commit": REGISTRATION_COMMIT,
        "g6": g6_identity,
        "g7": {
            "rows_recomputed": len(rows),
            "totals_recomputed_from_rows": True,
            "byte_identical_replay": True,
            "sealed_sha256": hashlib.sha256(sealed_bytes).hexdigest(),
            "replay_sha256": hashlib.sha256(replay_bytes).hexdigest(),
            "embedding_calls": 0,
            "model_generation_calls": 0,
        },
        "primary": {
            "budget": BUDGET,
            "n": len(rows),
            "session_all_evidence_hits": arms["S_SESSION_RANK"][
                "all_evidence_hits"
            ],
            "pair_all_evidence_hits": arms["P_PAIR_RANK"][
                "all_evidence_hits"
            ],
            "paired": comparison,
        },
        "secondary": {
            "arms": arms,
            "by_conversation": _group_summary(rows, "sample_id"),
            "by_category": _group_summary(rows, "category"),
        },
        "live_evaluation_boundary": (
            "Availability is not reader correctness; no live run, promotion, "
            "or adoption is authorized."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(canonical_bytes(payload))
    return payload
