from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.analysis.e002_segmented_query import (
    TURN_LOG,
    load_candidates,
    verify_e002_source_seal,
)
from src.embeddings.provider import cosine_similarity
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_mechanism_ledger.e001 import (
    select_cue,
    unit_scores,
    whitespace_units,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
PROTOCOL = COMPONENT_ROOT / "E001_attention_term_selection_protocol.md"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e001.py"
CAPTURE_SOURCE = REPO_ROOT / "src" / "analysis" / "e001_attention_capture.py"
ANALYSIS_SOURCE = Path(__file__).resolve()
PROBE_TURN = 115
TARGET_TURN = 55
CORRECTED_BASELINE = 0.12042197585105896
K_THRESHOLD = 0.48
SWEEP_FIELDS = (
    "arm",
    "probe_token_index",
    "probe_token",
    "k",
    "visible_unit_count",
    "selected_unit_indices",
    "selected_units",
    "attention_mass",
    "cue",
    "target_cosine",
    "baseline_delta",
    "target_similarity_rank",
    "k_eligible",
)


class EmbeddingCache:
    def __init__(self, embedder: CarriedEmbedder) -> None:
        self.embedder = embedder
        self.values = {}

    def prime(self, texts) -> None:
        missing = sorted(set(texts) - self.values.keys())
        if missing:
            values = self.embedder.embed_many(missing)
            self.values.update(zip(missing, values, strict=True))

    def __getitem__(self, text):
        return self.values[text]


def run_analysis(
    output_dir: Path,
    capture_dir: Path,
    embedding_model: Path,
) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite E001 analysis: {output_dir}")
    output_dir.mkdir(parents=True)
    execution_commit = _git("rev-parse", "HEAD")
    launch = analysis_launch_manifest(execution_commit)
    _write_json(output_dir / "launch_manifest.json", launch)

    inputs = [
        PROTOCOL,
        MECHANISM_SOURCE,
        CAPTURE_SOURCE,
        ANALYSIS_SOURCE,
        TURN_LOG,
        capture_dir / "capture_manifest.json",
        capture_dir / "q4_attention.npz",
        capture_dir / "q4_tokenization.json",
        capture_dir / "retrieval_heads.json",
    ]
    before = _hash_paths(inputs)
    seal = verify_e002_source_seal()
    if seal["status"] != "PASS":
        raise RuntimeError("Corrected Tier 6 mechanism seal failed")
    capture = _read_json(capture_dir / "capture_manifest.json")
    if capture["status"] != "PASS":
        raise RuntimeError("E001 attention capture did not pass")

    embedder = CarriedEmbedder(embedding_model)
    embedder.assert_carried_model()
    cache = EmbeddingCache(embedder)
    candidates = [
        candidate
        for candidate in load_candidates()
        if int(candidate["turn_number"]) < PROBE_TURN
    ]
    target = next(
        candidate
        for candidate in candidates
        if int(candidate["turn_number"]) == TARGET_TURN
    )
    query = probe_query()
    cache.prime([query])
    baseline = evaluate_cue(query, candidates, target, cache[query])
    if abs(baseline["target_cosine"] - CORRECTED_BASELINE) > 1e-7:
        raise RuntimeError("Corrected Q4 baseline did not reproduce")

    with np.load(capture_dir / "q4_attention.npz") as archive:
        attention = np.asarray(archive["attention"], dtype=np.float32)
        full_layer_ids = archive["full_layer_ids"].tolist()
    tokenization = _read_json(capture_dir / "q4_tokenization.json")
    heads_doc = _read_json(capture_dir / "retrieval_heads.json")
    retrieval_heads = [
        (int(row["layer_slot"]), int(row["head"]))
        for row in heads_doc["heads"]
    ]
    if tokenization["query"] != query:
        raise RuntimeError("Captured query differs from corrected probe")

    raw_rows = build_sweep_rows(
        query=query,
        attention=attention,
        tokenization=tokenization,
        retrieval_heads=retrieval_heads,
    )
    cache.prime(row["cue"] for row in raw_rows)
    rows = []
    for row in raw_rows:
        evaluation = evaluate_cue(
            row["cue"],
            candidates,
            target,
            cache[row["cue"]],
        )
        rows.append(
            {
                **row,
                **evaluation,
                "baseline_delta": (
                    evaluation["target_cosine"] - baseline["target_cosine"]
                ),
                "k_eligible": evaluation["target_cosine"] >= K_THRESHOLD,
            }
        )
    best = min(
        rows,
        key=lambda row: (
            -row["target_cosine"],
            row["target_similarity_rank"],
            row["k"],
            row["arm"],
            row["probe_token_index"],
        ),
    )
    outcome = (
        "F2_SIGNAL"
        if any(row["k_eligible"] for row in rows)
        else "KILL"
    )
    after = _hash_paths(inputs)
    execution_commit_after = _git("rev-parse", "HEAD")
    source_status = (
        "PASS"
        if before == after and execution_commit == execution_commit_after
        else "FAIL"
    )
    result = {
        "entry": "E001",
        "status": "COMPLETE" if source_status == "PASS" else "FAIL",
        "outcome": outcome,
        "scope": "Exploratory F2 diagnostic only; not a breadth bound.",
        "deployment_status": "NOT_DEPLOYABLE",
        "e003_disposition": "NOT_AUTHORIZED",
        "design_commit": "fd880d88",
        "execution_commit": execution_commit,
        "execution_commit_after": execution_commit_after,
        "launch": launch,
        "probe_turn": PROBE_TURN,
        "target_turn": TARGET_TURN,
        "generator_revision": capture["model_revision"],
        "generator_quantization": capture["quantization"],
        "embedding_model_sha256": _sha256(embedding_model),
        "expected_embedding_model_sha256": CARRIED_EMBEDDING_SHA256,
        "mechanism_seal_status": seal["status"],
        "capture_status": capture["status"],
        "capture_determinism_status": capture["determinism"]["status"],
        "source_integrity_status": source_status,
        "baseline": baseline,
        "corrected_baseline": CORRECTED_BASELINE,
        "k_threshold": K_THRESHOLD,
        "full_attention_layer_ids": full_layer_ids,
        "retrieval_head_count": len(retrieval_heads),
        "sweep_row_count": len(rows),
        "unique_cue_count": len({row["cue"] for row in rows}),
        "best": best,
        "interpretation": (
            "K eligibility only. Similarity rank is descriptive and is not "
            "the historical logical N rank. No live delivery claim."
        ),
    }
    _write_csv(output_dir / "cue_sweep.csv", rows, SWEEP_FIELDS)
    _write_json(output_dir / "best_cue.json", best)
    _write_json(output_dir / "e001_results.json", result)
    (output_dir / "E001_report.md").write_text(
        report(result),
        encoding="utf-8",
        newline="\n",
    )
    _write_json(
        output_dir / "source_integrity.json",
        {
            "status": source_status,
            "hashes_before": before,
            "hashes_after": after,
        },
    )
    _write_json(
        output_dir / "artifact_manifest.json",
        {
            path.name: _sha256(path)
            for path in sorted(output_dir.iterdir())
            if path.is_file() and path.name != "artifact_manifest.json"
        },
    )
    return result


def analysis_launch_manifest(execution_commit: str) -> dict:
    argv = [sys.executable, *sys.argv]
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "pid": os.getpid(),
        "cwd": str(Path.cwd().resolve()),
        "argv": argv,
        "command": subprocess.list2cmdline(argv),
        "execution_commit": execution_commit,
        "inference_server": {
            "used": False,
            "build_hash": None,
            "reason": "llama-cpp-python embeds in-process with the pinned local GGUF",
        },
    }


def build_sweep_rows(
    *,
    query: str,
    attention: np.ndarray,
    tokenization: dict,
    retrieval_heads: list[tuple[int, int]],
) -> list[dict]:
    query_token_count = int(tokenization["query_token_count"])
    offsets = tokenization["offsets"][:query_token_count]
    tokens = tokenization["tokens"]
    units = whitespace_units(query)
    rows = []
    for arm in ("all_heads", "retrieval_heads"):
        heads = None if arm == "all_heads" else retrieval_heads
        for row_index in range(1, int(tokenization["eos_token_index"]) + 1):
            if heads is None:
                token_attention = attention[
                    :, :, row_index, :query_token_count
                ].mean(axis=(0, 1))
            else:
                token_attention = np.asarray(
                    [
                        attention[layer, head, row_index, :query_token_count]
                        for layer, head in heads
                    ]
                ).mean(axis=0)
            visible_offsets = [
                offset
                for index, offset in enumerate(offsets)
                if index <= row_index
            ]
            visible_attention = token_attention[: len(visible_offsets)]
            scored = unit_scores(
                query,
                token_offsets=visible_offsets,
                token_scores=visible_attention,
            )
            visible = tuple(
                item for item in scored if item[0].start < int(visible_offsets[-1][1])
            )
            if not visible:
                continue
            for k in range(1, len(visible) + 1):
                cue, selected_indices, mass = select_cue(visible, k=k)
                rows.append(
                    {
                        "arm": arm,
                        "probe_token_index": row_index,
                        "probe_token": tokens[row_index],
                        "k": k,
                        "visible_unit_count": len(visible),
                        "selected_unit_indices": "|".join(
                            str(index) for index in selected_indices
                        ),
                        "selected_units": "|".join(
                            units[index].text for index in selected_indices
                        ),
                        "attention_mass": mass,
                        "cue": cue,
                    }
                )
    return rows


def evaluate_cue(query, candidates, target, query_vector):
    scored = [
        (
            str(candidate["id"]),
            cosine_similarity(
                np.asarray(query_vector, dtype=np.float32),
                _vector(candidate["embedding"]),
            ),
        )
        for candidate in candidates
    ]
    ranked = sorted(scored, key=lambda item: (-item[1], item[0]))
    target_id = str(target["id"])
    target_cosine = next(score for candidate_id, score in scored if candidate_id == target_id)
    rank = next(
        index
        for index, (candidate_id, _score) in enumerate(ranked, 1)
        if candidate_id == target_id
    )
    return {
        "cue": query,
        "target_id": target_id,
        "target_cosine": target_cosine,
        "target_similarity_rank": rank,
        "eligible_candidate_count": len(candidates),
    }


def probe_query() -> str:
    for line in TURN_LOG.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row["turn_number"]) == PROBE_TURN:
            return str(row["user_message"])
    raise RuntimeError("Q4 probe query is absent")


def report(result: dict) -> str:
    best = result["best"]
    return "\n".join(
        [
            "# E001 Attention-Derived Term Selection",
            "",
            f"**Outcome:** **{result['outcome']}**",
            "**Scope:** Exploratory F2 diagnostic only; not a breadth bound.",
            "**Deployment:** Not deployable.",
            "",
            "## Result",
            "",
            (
                f"The corrected full-query baseline cosine was "
                f"**{result['baseline']['target_cosine']:.9f}**, at descriptive "
                f"similarity rank **{result['baseline']['target_similarity_rank']}** "
                f"of {result['baseline']['eligible_candidate_count']}."
            ),
            (
                f"The best attention cue used `{best['arm']}`, selected "
                f"`{best['cue']}`, and reached cosine "
                f"**{best['target_cosine']:.9f}** at descriptive similarity "
                f"rank **{best['target_similarity_rank']}**."
            ),
            (
                f"K threshold {result['k_threshold']:.2f}: "
                f"**{'REACHED' if best['k_eligible'] else 'NOT REACHED'}**."
            ),
            "",
            "## Integrity",
            "",
            (
                f"Source seal: **{result['mechanism_seal_status']}**. "
                f"Capture: **{result['capture_status']}**. "
                f"Deterministic rerun: **{result['capture_determinism_status']}**. "
                f"Source integrity: **{result['source_integrity_status']}**."
            ),
            "",
            (
                "Similarity rank is not the historical logical N rank, and K "
                "eligibility does not certify delivery under N-first packing. "
                "E003 remains not authorized because E001 has no breadth arm."
            ),
            "",
        ]
    )


def _vector(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        return np.frombuffer(value, dtype=np.float32).copy()
    return np.asarray(value, dtype=np.float32)


def _write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_paths(paths):
    return {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(path)
        for path in paths
    }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args):
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    args = parser.parse_args()
    result = run_analysis(
        args.output_dir,
        args.capture_dir.resolve(),
        args.embedding_model.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
