"""NF-002 gate evaluation against the locked registration.

Bars are repeated from `NF_002_PRE_REGISTRATION.md` §5 as constants so a run
reproduces from committed code. They are not parameters.

The statistic is paired discordant counts with a one-sided exact binomial sign
test. Only items where the two arms disagree contribute, so no base rate can
carry it and no degenerate arm can win it. Every p is reported next to the
discordant-pair count it came from, because §5's mirror question is answered
"yes" here: at this power a real effect can miss the upper tier on sampling.
"""

from __future__ import annotations

import hashlib
import json
from math import comb
from pathlib import Path
from typing import Any, Sequence

from analysis import nf002_streams as streams_module
from analysis.nf002_streams import QuestionStream, pack_all, pack_episodes

SPLIT_SEED = "5005"
SPLIT_DOMAIN = "nf002-split-v1"
DEVELOPMENT_SHARE = 0.40

TIERS = {
    "WORKS": {"min_gain_ratio": 2.0, "max_p": 0.05},
    "CARRIES_SIGNAL": {"min_gain_ratio": 1.0, "max_p": 0.20},
}


def _rank(question_id: str) -> str:
    return hashlib.sha256(
        f"{SPLIT_SEED}\0{SPLIT_DOMAIN}\0{question_id}".encode("utf-8")
    ).hexdigest()


def assign_split(items: Sequence[QuestionStream]) -> dict[str, str]:
    """Stratified by question_type so every type appears in both halves."""
    assignment: dict[str, str] = {}
    by_type: dict[str, list[QuestionStream]] = {}
    for stream in items:
        by_type.setdefault(stream.question_type, []).append(stream)
    for _question_type, group in sorted(by_type.items()):
        ordered = sorted(group, key=lambda s: _rank(s.question_id))
        cut = int(len(ordered) * DEVELOPMENT_SHARE)
        for index, stream in enumerate(ordered):
            assignment[stream.question_id] = "development" if index < cut else "holdout"
    return assignment


def sign_test(gains: int, losses: int) -> float:
    """One-sided exact binomial p that gains exceed losses by chance."""
    n = gains + losses
    if n == 0:
        return 1.0
    return sum(comb(n, k) for k in range(gains, n + 1)) / 2**n


def paired_counts(items: Sequence[QuestionStream], measure: str) -> dict[str, int]:
    gains = losses = ties = 0
    for stream in items:
        if measure == "any_evidence":
            base = pack_all(stream)[0] >= 1
            treat = pack_episodes(stream)[0] >= 1
        elif measure == "all_evidence":
            base = pack_all(stream)[0] >= stream.evidence_total
            treat = pack_episodes(stream)[0] >= stream.evidence_total
        else:
            raise ValueError(measure)
        if treat and not base:
            gains += 1
        elif base and not treat:
            losses += 1
        else:
            ties += 1
    return {"gains": gains, "losses": losses, "ties": ties}


def disposition(gains: int, losses: int) -> tuple[str, float]:
    p = sign_test(gains, losses)
    ratio = (gains / losses) if losses else float("inf")
    if ratio >= TIERS["WORKS"]["min_gain_ratio"] and p <= TIERS["WORKS"]["max_p"]:
        return "WORKS", p
    if gains > losses and p <= TIERS["CARRIES_SIGNAL"]["max_p"]:
        return "CARRIES_SIGNAL", p
    return "NULL", p


def evaluate(repository_root: Path) -> dict[str, Any]:
    items, anchor = streams_module.load_streams()
    assignment = assign_split(items)
    by_split = {
        "development": [s for s in items if assignment[s.question_id] == "development"],
        "holdout": [s for s in items if assignment[s.question_id] == "holdout"],
        "all": list(items),
    }

    results: dict[str, Any] = {}
    for split, group in by_split.items():
        entry: dict[str, Any] = {"n": len(group)}
        for measure in ("any_evidence", "all_evidence"):
            counts = paired_counts(group, measure)
            verdict, p = disposition(counts["gains"], counts["losses"])
            entry[measure] = {
                **counts,
                "discordant_pairs": counts["gains"] + counts["losses"],
                "net": counts["gains"] - counts["losses"],
                "p_one_sided": p,
                "disposition": verdict,
            }
        results[split] = entry

    # Per-stratum, reported and unable to pass anything.
    strata: dict[str, Any] = {}
    for stream in items:
        strata.setdefault(stream.question_type, []).append(stream)
    per_stratum = {}
    for name, group in sorted(strata.items()):
        counts = paired_counts(group, "any_evidence")
        per_stratum[name] = {
            **counts,
            "n": len(group),
            "p_one_sided": sign_test(counts["gains"], counts["losses"]),
        }

    def rate(fn) -> dict[str, Any]:
        hits = sum(1 for s in items if fn(s)[0] >= 1)
        return {"any_evidence": hits, "rate": hits / len(items)}

    return {
        "schema": "nf002-gates-v1",
        "anchor": anchor,
        "tiers": TIERS,
        "split": {
            "seed": SPLIT_SEED,
            "development_share": DEVELOPMENT_SHARE,
            "stratified_by": "question_type",
        },
        "results": results,
        "per_stratum_any_evidence": per_stratum,
        "arms": {
            "A0_sessions": rate(pack_all),
            "A1_episodes": rate(pack_episodes),
            "oracle_ceiling": rate(streams_module.pack_oracle),
        },
        "deviation": "DEVIATION_001: holdout observed before the bars were locked; "
        "the highest available disposition is CHARACTERIZED, not confirmatory.",
    }


def write_report(repository_root: Path) -> Path:
    record = evaluate(repository_root)
    path = (
        repository_root
        / "experiments/components/biological_memory/nf_002/artifacts/gates.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
