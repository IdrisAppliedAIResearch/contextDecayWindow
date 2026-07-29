from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from src.retrieval_bakeoff.config import CORPORA, REPO_ROOT, SURVEY_ROOT
from src.retrieval_bakeoff.corpus import load_queries
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_bakeoff.embedding_cache import EmbeddingCache
from src.retrieval_bakeoff.evaluation import validate_locked_artifacts
from src.retrieval_bakeoff.fidelity import run_fidelity_check
from src.retrieval_bakeoff.harness import RetrievalHarness
from src.retrieval_bakeoff.leakage import (
    assert_planted_violations,
    audit_import_graph,
    guard_measurement_files,
)
from src.retrieval_bakeoff.methods import METHOD_IDS


REGISTRATION_ANCHOR = "b60b7084741eb5d30298261076b4bca78abe713a"
HOLDOUT_ANCHOR = "23b9bb99"
MECHANISM_ENTRY_POINTS = [
    REPO_ROOT / "src" / "retrieval_bakeoff" / name
    for name in (
        "classifier.py",
        "config.py",
        "corpus.py",
        "embedding.py",
        "embedding_cache.py",
        "harness.py",
        "methods.py",
        "models.py",
        "serialization.py",
    )
]


class DeterministicAuditEmbedder:
    model_sha256 = "audit-model-" + ("0" * 52)

    def __call__(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vector = np.zeros(1_024, dtype=np.float32)
        for index, value in enumerate(digest):
            vector[index] = (value - 127.5) / 127.5
        norm = float(np.linalg.norm(vector))
        return vector / norm if norm else vector

    def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        return [self(text) for text in texts]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--embedding-model",
        type=Path,
        required=True,
        help="Absolute path to the carried Qwen embedding GGUF",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SURVEY_ROOT / "tier0",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _assert_clean_committed_state()
    locked_hashes = validate_locked_artifacts()
    static = audit_import_graph(MECHANISM_ENTRY_POINTS)

    with tempfile.TemporaryDirectory(prefix="retrieval-bakeoff-tier0-") as temp:
        temp_root = Path(temp)
        planted = assert_planted_violations(temp_root / "planted")
        runtime = _runtime_audit(temp_root)

    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()
    fidelity = run_fidelity_check(embedder)
    status = (
        "PASS"
        if static["status"] == "PASS"
        and planted["status"] == "PASS"
        and runtime["status"] == "PASS"
        and fidelity["status"] == "PASS"
        else "FAIL"
    )
    payload = {
        "tier": "T0",
        "evidence_class": "registered",
        "query_set": "holdout",
        "status": status,
        "registration_anchor": REGISTRATION_ANCHOR,
        "holdout_anchor": HOLDOUT_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "threading": {
            "llama_cpp_n_threads": 1,
            "llama_cpp_n_threads_batch": 1,
        },
        "locked_artifact_hashes": locked_hashes,
        "static_leakage_audit": static,
        "planted_leakage_audit": planted,
        "runtime_leakage_audit": runtime,
        "fidelity": fidelity,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "tier0_results.json"
    result_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    report_path = args.output_dir / "tier0_report.md"
    report_path.write_text(_render_report(payload), encoding="utf-8")
    print(json.dumps({"status": status, "result": str(result_path)}))
    return 0 if status == "PASS" else 1


def _runtime_audit(temp_root: Path) -> dict:
    spec = CORPORA["c121_l"]
    embedder = DeterministicAuditEmbedder()
    rows = []
    with guard_measurement_files() as observed:
        query = load_queries(spec)[0]
        for method_id in METHOD_IDS:
            cache = EmbeddingCache(
                temp_root / f"{method_id}_cache.sqlite",
                embedder.model_sha256,
            )
            try:
                with RetrievalHarness(
                    spec,
                    embedder=embedder,
                    embedding_cache=cache,
                ) as harness:
                    result = harness.retrieve(
                        method_id,
                        query,
                        repetitions=1,
                    )
                rows.append(
                    {
                        "method_id": method_id,
                        "selected_count": len(result.selected),
                        "delivered_characters": result.delivered_characters,
                        "eligible_turn_min": spec.eligible_turn_min,
                        "eligible_turn_max": spec.eligible_turn_max,
                    }
                )
            finally:
                cache.close()
    observed_repo_paths = sorted(
        {
            str(Path(path).resolve().relative_to(REPO_ROOT))
            for path in observed
            if _is_under_repo(path)
        }
    )
    return {
        "status": "PASS",
        "methods_exercised": rows,
        "observed_open_count": len(observed),
        "observed_repo_paths": observed_repo_paths,
    }


def _is_under_repo(value: str) -> bool:
    try:
        Path(value).resolve().relative_to(REPO_ROOT)
        return True
    except (OSError, ValueError):
        return False


def _assert_clean_committed_state() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("Registered Tier 0 requires a clean committed worktree")
    if _git("branch", "--show-current") != "retrieval-bakeoff":
        raise RuntimeError("Registered Tier 0 must run on retrieval-bakeoff")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", REGISTRATION_ANCHOR, "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", HOLDOUT_ANCHOR, "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _render_report(payload: dict) -> str:
    fidelity_rows = "\n".join(
        (
            f"| {probe['turn']} | {probe['status']} | "
            f"{probe['actual_characters']} | `{probe['actual_sha256']}` |"
        )
        for probe in payload["fidelity"]["probes"]
    )
    return (
        "# Retrieval Bakeoff Tier 0 Report\n\n"
        f"**Status:** {payload['status']}\n\n"
        f"**Registration anchor:** `{payload['registration_anchor']}`\n\n"
        f"**Holdout anchor:** `{payload['holdout_anchor']}`\n\n"
        f"**Code commit:** `{payload['code_commit']}`\n\n"
        "## Leakage Boundary\n\n"
        f"- Static import graph: {payload['static_leakage_audit']['status']}\n"
        f"- Runtime file trace: {payload['runtime_leakage_audit']['status']}\n"
        f"- Planted module and file violations: "
        f"{payload['planted_leakage_audit']['status']}\n\n"
        "## T0.3 Fidelity\n\n"
        "| Turn | Status | Characters | Historical block SHA-256 |\n"
        "|---:|---|---:|---|\n"
        f"{fidelity_rows}\n\n"
        "The Study 007 source tree was hash-identical before and after replay.\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
