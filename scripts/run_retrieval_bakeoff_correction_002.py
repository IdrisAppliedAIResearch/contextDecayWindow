from __future__ import annotations

import os

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

from src.retrieval_bakeoff.config import REPO_ROOT, SURVEY_ROOT
from src.retrieval_bakeoff.correction_002 import run_corrected_k_diagnostic
from src.retrieval_bakeoff.embedding import CarriedEmbedder
from src.retrieval_bakeoff.evaluation import aggregate_rows
from src.retrieval_bakeoff.k_collapse import STORES
from src.retrieval_bakeoff.tier3_analysis import analyze_tier3


ORIGINAL_RESULT_ANCHOR = "29c5150d"
AMENDMENT_ANCHOR = "7b9994b1"
EVALUATION_PATH = SURVEY_ROOT / "tier2" / "evaluation_results.jsonl"
OUTPUT_ROOT = SURVEY_ROOT / "corrections" / "amendment_002"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--embedding-model", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _assert_ready()
    source_paths = [
        EVALUATION_PATH,
        *[run / "study.db" for run in STORES.values()],
        *[run / "logs" / "retrieval.jsonl" for run in STORES.values()],
    ]
    hashes_before = _hash_files(source_paths)
    rows = [
        json.loads(line)
        for line in EVALUATION_PATH.read_text(encoding="utf-8").splitlines()
    ]
    if len(rows) != 528:
        raise AssertionError("Committed Tier 2 evaluation row count changed")

    embedder = CarriedEmbedder(args.embedding_model)
    embedder.assert_carried_model()
    embedder.warmup()
    k_diagnostic = run_corrected_k_diagnostic(embedder)
    tier2_summary = aggregate_rows(rows)
    tier3 = analyze_tier3(rows, tier2_summary)
    hashes_after = _hash_files(source_paths)
    if hashes_before != hashes_after:
        raise RuntimeError("A correction source artifact changed during analysis")

    payload = {
        "correction": "AMENDMENT_002",
        "status": "COMPLETE",
        "original_result_anchor": ORIGINAL_RESULT_ANCHOR,
        "amendment_anchor": AMENDMENT_ANCHOR,
        "code_commit": _git("rev-parse", "HEAD"),
        "model_path": str(embedder.model_path),
        "model_sha256": embedder.model_sha256,
        "source_hashes_before": hashes_before,
        "source_hashes_after": hashes_after,
        "T1.3_corrected": k_diagnostic,
        "T2_corrected_summary": tier2_summary,
        "T3_corrected_analysis": tier3,
    }
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / "corrected_analysis.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_ROOT / "corrected_report.md").write_text(
        _report(payload),
        encoding="utf-8",
    )
    _write_distribution(
        OUTPUT_ROOT / "k_similarity_distribution_corrected.csv",
        k_diagnostic,
    )
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "mechanism": k_diagnostic["most_likely_mechanism"],
            }
        )
    )
    return 0


def _write_distribution(path: Path, payload: dict) -> None:
    fields = [
        "store_id",
        "turn_number",
        "episode_id",
        "stored_similarity",
        "recomputed_pair_similarity",
        "recomputed_user_similarity",
        "assistant_swap_similarity",
        "script_swap_similarity",
        "stored_recomputed_threshold_crossing",
        "user_message_matches_other_store",
        "assistant_characters",
        "other_assistant_characters",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for store_id, store in payload["stores"].items():
            for row in store["distribution"]:
                writer.writerow({"store_id": store_id, **row})


def _report(payload: dict) -> str:
    diagnostic = payload["T1.3_corrected"]
    store_lines = []
    for store_id, store in diagnostic["stores"].items():
        summaries = store["summaries"]
        store_lines.append(
            f"| {store_id} | {store['historical_k_count']} | "
            f"{summaries['stored']['at_or_above_0_50']} | "
            f"{summaries['recomputed_pair']['at_or_above_0_50']} | "
            f"{summaries['recomputed_user']['at_or_above_0_50']} | "
            f"{summaries['assistant_swap']['at_or_above_0_50']} | "
            f"{store['stored_recomputed_threshold_crossings']} |"
        )
    advancement_lines = [
        f"- `{row['method_id']}`: "
        f"{'ADVANCES' if row['advances'] else 'DOES NOT ADVANCE'}; "
        f"wins={','.join(row['winning_classes']) or 'none'}; "
        f"regressions={','.join(row['regressing_classes']) or 'none'}."
        for row in payload["T2_corrected_summary"]["advancement"]
    ]
    router = payload["T3_corrected_analysis"]["T3.2_oracle_router"]
    return (
        "# Retrieval Bakeoff Amendment 002 Correction\n\n"
        f"**Original result anchor:** `{payload['original_result_anchor']}`\n\n"
        f"**Amendment anchor:** `{payload['amendment_anchor']}`\n\n"
        "## Corrected T1.3\n\n"
        "| Store | Historical K | Stored K | Recomputed pair K | "
        "User-only K | Assistant-swap K | Replay threshold crossings |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
        + "\n".join(store_lines)
        + "\n\n"
        f"Most likely mechanism: "
        f"`{diagnostic['most_likely_mechanism']}`.\n\n"
        "## Exact Advancement\n\n"
        + "\n".join(advancement_lines)
        + "\n\n"
        "## Exact Routing Bound\n\n"
        f"Oracle recall `{router['oracle_macro_query_recall_exact']}` versus "
        f"single-best `{router['single_best_macro_query_recall_exact']}`; "
        f"relative gain `{router['relative_gain_exact']}`. "
        f"Interpretation: `{router['interpretation']}`.\n"
    )


def _hash_files(paths: list[Path]) -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in paths
    }


def _assert_ready() -> None:
    if _git("status", "--porcelain"):
        raise RuntimeError("Correction 002 requires a clean committed worktree")
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Correction output already exists: {OUTPUT_ROOT}")
    for anchor in (ORIGINAL_RESULT_ANCHOR, AMENDMENT_ANCHOR):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", anchor, "HEAD"],
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


if __name__ == "__main__":
    raise SystemExit(main())
