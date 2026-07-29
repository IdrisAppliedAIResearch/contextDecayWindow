from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

from src.retrieval_bakeoff.config import REPO_ROOT
from src.retrieval_bakeoff.reinforcement import analyze_reinforcement


OUTPUT_ROOT = (
    REPO_ROOT
    / "experiments/surveys/retrieval_bakeoff/tier1/t1_3_reinforcement"
)


def main() -> None:
    implementation_sha = _require_clean_committed_tree()
    if OUTPUT_ROOT.exists():
        raise RuntimeError(f"Refusing to overwrite {OUTPUT_ROOT}")

    result = analyze_reinforcement(implementation_sha=implementation_sha)
    OUTPUT_ROOT.mkdir(parents=True)
    _write_json(OUTPUT_ROOT / "reinforcement_results.json", result)
    _write_per_turn_csv(OUTPUT_ROOT / "per_turn_overlap.csv", result)
    _write_quartile_csv(OUTPUT_ROOT / "quartile_summary.csv", result)
    (OUTPUT_ROOT / "t1_3_reinforcement_report.md").write_text(
        _render_report(result),
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "verdict": result["verdict"],
                "implementation_sha": implementation_sha,
                "output_root": str(OUTPUT_ROOT.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


def _require_clean_committed_tree() -> str:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    if status.strip():
        raise RuntimeError(
            "Commit implementation and tests before running the diagnostic"
        )
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
            default=_json_default,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_per_turn_csv(path: Path, result: dict) -> None:
    fields = [
        "corpus_id",
        "turn_number",
        "normalized_position",
        "quartile",
        "k_count",
        "overlap_count",
        "k_only_count",
        "n_count",
        "overlap_fraction_exact",
        "overlap_fraction",
    ]
    rows = [
        row
        for corpus in result["corpora"]
        for row in corpus["per_turn"]
    ]
    _write_csv(path, fields, rows)


def _write_quartile_csv(path: Path, result: dict) -> None:
    fields = [
        "corpus_id",
        "quartile",
        "first_turn",
        "last_turn",
        "turn_count",
        "evaluable_turn_count",
        "k_count",
        "overlap_count",
        "k_only_count",
        "overlap_fraction_exact",
        "overlap_fraction",
    ]
    rows = [
        {"corpus_id": corpus["corpus_id"], **quartile}
        for corpus in result["corpora"]
        for quartile in corpus["quartiles"]
    ]
    _write_csv(path, fields, rows)


def _write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: (
                        _json_default(value)
                        if key == "normalized_position"
                        else value
                    )
                    for key, value in row.items()
                }
            )


def _render_report(result: dict) -> str:
    lines = [
        "# T1.3 N/K Reinforcement Supplement",
        "",
        f"**Amendment:** `{result['amendment_anchor']}`  ",
        f"**Implementation:** `{result['implementation_sha']}`  ",
        f"**Hypothesis:** `{result['hypothesis_id']}`  ",
        f"**Verdict:** **{result['verdict']}**",
        "",
        "## Results",
        "",
        "| Corpus | K candidates | K in N | Q1 overlap | Q4 overlap | Delta | OLS slope | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for corpus in result["corpora"]:
        q1 = corpus["quartiles"][0]["overlap_fraction"]
        q4 = corpus["quartiles"][3]["overlap_fraction"]
        lines.append(
            "| "
            f"{corpus['corpus_id']} | "
            f"{corpus['total_k_candidates']} | "
            f"{corpus['total_overlap_candidates']} | "
            f"{_percent(q1)} | "
            f"{_percent(q4)} | "
            f"{_signed_percent(corpus['primary_delta'])} | "
            f"{_number(corpus['ols_slope'])} | "
            f"{corpus['support_status']} |"
        )
    lines.extend(
        [
            "",
            "The registered hypothesis is confirmed only if both corpora have "
            "a positive Q4-minus-Q1 micro-overlap delta and a positive "
            "per-turn OLS slope. These are deterministic census summaries; "
            "no p-value is used.",
            "",
            "## Integrity",
            "",
        ]
    )
    for corpus in result["corpora"]:
        lines.append(
            f"- `{corpus['corpus_id']}`: {corpus['turn_count']} contiguous "
            f"turns, {corpus['evaluable_turn_count']} with K candidates, "
            f"all accounting and temporal invariants PASS; source SHA-256 "
            f"`{corpus['source_sha256']}`."
        )
    lines.extend(
        [
            "",
            "This supplement is descriptive and does not alter the completed "
            "T1.3 similarity result or any method-advancement decision.",
            "",
        ]
    )
    return "\n".join(lines)


def _json_default(value: object) -> str:
    numerator = getattr(value, "numerator", None)
    denominator = getattr(value, "denominator", None)
    if numerator is not None and denominator is not None:
        return f"{numerator}/{denominator}"
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2%}"


def _signed_percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2%}"


def _number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.6f}"


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
