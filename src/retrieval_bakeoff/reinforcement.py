from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .config import REPO_ROOT


AMENDMENT_ANCHOR = "39ba9175"
HYPOTHESIS_ID = "H_T1.3_NK_REINFORCEMENT"


@dataclass(frozen=True)
class ReinforcementInput:
    corpus_id: str
    path: Path
    expected_turns: int
    expected_sha256: str


LOCKED_INPUTS = (
    ReinforcementInput(
        corpus_id="study_009_arm_s",
        path=(
            REPO_ROOT
            / "experiments/study_009/runs/study_009_full_001/arm_s"
            / "logs/retrieval.jsonl"
        ),
        expected_turns=121,
        expected_sha256=(
            "c948eaca81450cad14283b57591cdc2355011d797c885c84688d94acc37a9ddb"
        ),
    ),
    ReinforcementInput(
        corpus_id="study_010_arm_s",
        path=(
            REPO_ROOT
            / "experiments/study_010/runs/study_010_full_001/arm_s"
            / "logs/retrieval.jsonl"
        ),
        expected_turns=1_000,
        expected_sha256=(
            "e57dd5d170421da699abd094f304df3e783c559ca7997f183e4ad118b9e3f414"
        ),
    ),
)


def analyze_reinforcement(
    *,
    inputs: tuple[ReinforcementInput, ...] = LOCKED_INPUTS,
    implementation_sha: str,
) -> dict:
    if not implementation_sha:
        raise ValueError("implementation_sha is required")
    if len(inputs) != 2:
        raise AssertionError("The locked diagnostic requires exactly two corpora")

    corpora = [
        analyze_retrieval_log(spec)
        for spec in inputs
    ]
    source_hashes_after = {
        row.corpus_id: sha256_file(row.path)
        for row in inputs
    }
    for spec in inputs:
        if source_hashes_after[spec.corpus_id] != spec.expected_sha256:
            raise AssertionError(
                f"{spec.corpus_id}: source changed during analysis"
            )

    verdict = classify_hypothesis(corpora)
    return {
        "test_id": "T1.3_SUPPLEMENT_AMENDMENT_012",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "COMPLETE",
        "verdict": verdict,
        "decision_rule": {
            "quartile_formula": (
                "min(4, 1 + floor(4 * (turn - 1) / total_turns))"
            ),
            "primary_fraction": "sum(overlap_count) / sum(k_count)",
            "primary_delta": "quartile_4_fraction - quartile_1_fraction",
            "direction_check": (
                "OLS slope of per-turn overlap fraction against normalized "
                "conversation position"
            ),
            "corpus_support": "primary_delta > 0 and ols_slope > 0",
            "combined_confirmation": "both corpora support",
        },
        "implementation_sha": implementation_sha,
        "amendment_anchor": AMENDMENT_ANCHOR,
        "source_hashes_before": {
            spec.corpus_id: spec.expected_sha256 for spec in inputs
        },
        "source_hashes_after": source_hashes_after,
        "corpora": corpora,
    }


def analyze_retrieval_log(spec: ReinforcementInput) -> dict:
    observed_sha256 = sha256_file(spec.path)
    if observed_sha256 != spec.expected_sha256:
        raise AssertionError(
            f"{spec.corpus_id}: source hash mismatch; expected "
            f"{spec.expected_sha256}, observed {observed_sha256}"
        )
    rows = _read_jsonl(spec.path)
    if len(rows) != spec.expected_turns:
        raise AssertionError(
            f"{spec.corpus_id}: expected {spec.expected_turns} rows, "
            f"observed {len(rows)}"
        )

    per_turn = [
        _account_turn(
            corpus_id=spec.corpus_id,
            row=row,
            expected_turn=turn,
            total_turns=spec.expected_turns,
        )
        for turn, row in enumerate(rows, start=1)
    ]
    quartiles = [
        _summarize_quartile(per_turn, quartile)
        for quartile in range(1, 5)
    ]
    first_fraction = _fraction_from_summary(quartiles[0])
    final_fraction = _fraction_from_summary(quartiles[3])
    evaluable = [
        row for row in per_turn if row["overlap_fraction"] is not None
    ]
    slope = _ols_slope(evaluable, spec.expected_turns)

    reasons = []
    if first_fraction is None:
        reasons.append("quartile_1_has_no_k_candidates")
    if final_fraction is None:
        reasons.append("quartile_4_has_no_k_candidates")
    if slope is None:
        reasons.append("fewer_than_two_evaluable_turns")

    if reasons:
        support_status = "NOT_EVALUABLE"
        delta = None
    else:
        assert first_fraction is not None
        assert final_fraction is not None
        assert slope is not None
        delta = final_fraction - first_fraction
        support_status = (
            "SUPPORTS"
            if delta > 0 and slope > 0
            else "DOES_NOT_SUPPORT"
        )

    return {
        "corpus_id": spec.corpus_id,
        "source_path": _display_path(spec.path),
        "source_sha256": observed_sha256,
        "turn_count": spec.expected_turns,
        "evaluable_turn_count": len(evaluable),
        "zero_k_turn_count": spec.expected_turns - len(evaluable),
        "total_k_candidates": sum(row["k_count"] for row in per_turn),
        "total_overlap_candidates": sum(
            row["overlap_count"] for row in per_turn
        ),
        "quartiles": quartiles,
        "primary_delta_exact": _fraction_text(delta),
        "primary_delta": float(delta) if delta is not None else None,
        "ols_slope": slope,
        "support_status": support_status,
        "not_evaluable_reasons": reasons,
        "invariants": {
            "status": "PASS",
            "source_hash": "PASS",
            "row_count": "PASS",
            "contiguous_turns": "PASS",
            "k_identity": "PASS",
            "n_count": "PASS",
            "block_identity": "PASS",
            "temporal_eligibility": "PASS",
        },
        "per_turn": per_turn,
    }


def classify_hypothesis(corpora: list[dict]) -> str:
    statuses = [row["support_status"] for row in corpora]
    if any(status == "NOT_EVALUABLE" for status in statuses):
        return "NOT_EVALUABLE"
    support_count = statuses.count("SUPPORTS")
    if support_count == len(statuses):
        return "CONFIRMED_ON_PRESERVED_RUNS"
    if support_count:
        return "MIXED"
    return "NOT_CONFIRMED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if any(not line.strip() for line in lines):
        raise AssertionError(f"Blank JSONL row in {path}")
    rows = []
    for line_number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"Invalid JSON in {path} line {line_number}"
            ) from exc
        if not isinstance(row, dict):
            raise AssertionError(
                f"Non-object JSON in {path} line {line_number}"
            )
        rows.append(row)
    return rows


def _account_turn(
    *,
    corpus_id: str,
    row: dict,
    expected_turn: int,
    total_turns: int,
) -> dict:
    turn = _nonnegative_int(row.get("turn_number"), "turn_number", corpus_id)
    if turn != expected_turn:
        raise AssertionError(
            f"{corpus_id}: expected turn {expected_turn}, observed {turn}"
        )
    k_count = _nonnegative_int(row.get("k_count"), "k_count", corpus_id)
    n_count = _nonnegative_int(row.get("n_count"), "n_count", corpus_id)
    k_episodes = _episode_list(row.get("k_episodes"), "k_episodes", corpus_id)
    n_episodes = _episode_list(row.get("n_episodes"), "n_episodes", corpus_id)

    if n_count != len(n_episodes):
        raise AssertionError(
            f"{corpus_id} turn {turn}: n_count does not match n_episodes"
        )
    _validate_episode_block(
        corpus_id,
        turn,
        k_episodes,
        allowed_types={"K"},
        block_name="k_episodes",
    )
    _validate_episode_block(
        corpus_id,
        turn,
        n_episodes,
        allowed_types={"N", "KN"},
        block_name="n_episodes",
    )

    k_ids = {str(episode["id"]) for episode in k_episodes}
    n_ids = {str(episode["id"]) for episode in n_episodes}
    if k_ids & n_ids:
        raise AssertionError(
            f"{corpus_id} turn {turn}: N and K-only blocks overlap"
        )

    overlap_count = sum(
        episode["retrieval_type"] == "KN" for episode in n_episodes
    )
    k_only_count = len(k_episodes)
    if k_count != overlap_count + k_only_count:
        raise AssertionError(
            f"{corpus_id} turn {turn}: k_count={k_count}, but "
            f"KN + K-only={overlap_count + k_only_count}"
        )

    fraction = (
        Fraction(overlap_count, k_count)
        if k_count > 0
        else None
    )
    return {
        "corpus_id": corpus_id,
        "turn_number": turn,
        "normalized_position": (
            Fraction(turn - 1, total_turns - 1)
            if total_turns > 1
            else Fraction(0)
        ),
        "quartile": min(4, 1 + (4 * (turn - 1)) // total_turns),
        "k_count": k_count,
        "overlap_count": overlap_count,
        "k_only_count": k_only_count,
        "n_count": n_count,
        "overlap_fraction_exact": _fraction_text(fraction),
        "overlap_fraction": (
            float(fraction) if fraction is not None else None
        ),
    }


def _nonnegative_int(value: object, field: str, corpus_id: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AssertionError(
            f"{corpus_id}: {field} must be a non-negative integer"
        )
    return value


def _episode_list(value: object, field: str, corpus_id: str) -> list[dict]:
    if not isinstance(value, list) or any(
        not isinstance(item, dict) for item in value
    ):
        raise AssertionError(f"{corpus_id}: {field} must be a list of objects")
    return value


def _validate_episode_block(
    corpus_id: str,
    turn: int,
    episodes: list[dict],
    *,
    allowed_types: set[str],
    block_name: str,
) -> None:
    ids = []
    for episode in episodes:
        episode_id = episode.get("id")
        if not isinstance(episode_id, str) or not episode_id:
            raise AssertionError(
                f"{corpus_id} turn {turn}: invalid ID in {block_name}"
            )
        ids.append(episode_id)
        source_turn = _nonnegative_int(
            episode.get("turn_number"),
            f"{block_name}.turn_number",
            corpus_id,
        )
        if source_turn < 1 or source_turn >= turn:
            raise AssertionError(
                f"{corpus_id} turn {turn}: ineligible source turn "
                f"{source_turn} in {block_name}"
            )
        retrieval_type = episode.get("retrieval_type")
        if retrieval_type not in allowed_types:
            raise AssertionError(
                f"{corpus_id} turn {turn}: invalid retrieval_type "
                f"{retrieval_type!r} in {block_name}"
            )
    if len(ids) != len(set(ids)):
        raise AssertionError(
            f"{corpus_id} turn {turn}: duplicate ID in {block_name}"
        )


def _summarize_quartile(per_turn: list[dict], quartile: int) -> dict:
    rows = [row for row in per_turn if row["quartile"] == quartile]
    if not rows:
        raise AssertionError(f"Quartile {quartile} has no turns")
    k_count = sum(row["k_count"] for row in rows)
    overlap_count = sum(row["overlap_count"] for row in rows)
    fraction = (
        Fraction(overlap_count, k_count)
        if k_count > 0
        else None
    )
    return {
        "quartile": quartile,
        "first_turn": rows[0]["turn_number"],
        "last_turn": rows[-1]["turn_number"],
        "turn_count": len(rows),
        "evaluable_turn_count": sum(
            row["overlap_fraction"] is not None for row in rows
        ),
        "k_count": k_count,
        "overlap_count": overlap_count,
        "k_only_count": sum(row["k_only_count"] for row in rows),
        "overlap_fraction_exact": _fraction_text(fraction),
        "overlap_fraction": (
            float(fraction) if fraction is not None else None
        ),
    }


def _fraction_from_summary(summary: dict) -> Fraction | None:
    if summary["k_count"] == 0:
        return None
    return Fraction(summary["overlap_count"], summary["k_count"])


def _ols_slope(rows: list[dict], total_turns: int) -> float | None:
    if len(rows) < 2 or total_turns < 2:
        return None
    xs = [
        (row["turn_number"] - 1) / (total_turns - 1)
        for row in rows
    ]
    ys = [float(row["overlap_fraction"]) for row in rows]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    if denominator == 0:
        return None
    return sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(xs, ys, strict=True)
    ) / denominator


def _fraction_text(value: Fraction | None) -> str | None:
    if value is None:
        return None
    return f"{value.numerator}/{value.denominator}"


def _display_path(path: Path) -> str:
    try:
        displayed = path.relative_to(REPO_ROOT)
    except ValueError:
        displayed = path
    return str(displayed).replace("\\", "/")
