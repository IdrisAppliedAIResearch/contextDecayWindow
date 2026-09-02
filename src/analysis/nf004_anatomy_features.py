"""Evidence-blind feature extraction for the NF-004 item-anatomy audit."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.nf004_mechanism import Candidate, pack, ranking_orders
from retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256

DATASET_SHA256 = "79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
DATASET_BYTES = 2_805_274
HOLDOUT_IDS = frozenset({"conv-26", "conv-30", "conv-43", "conv-44", "conv-49", "conv-50"})
BUDGET = 16_000
_SESSION = re.compile(r"session_(\d+)")
_WORD = re.compile(r"[A-Za-z0-9]+")

FEATURE_FAMILIES: dict[str, tuple[str, ...]] = {
    "query_surface": (
        "query_chars", "query_words", "query_unique_fraction", "query_digits", "query_question_marks",
    ),
    "own_score_shape": (
        "score_max", "score_second", "score_top_gap", "score_mean", "score_std",
        "score_p90_p50", "score_within_001", "score_within_003", "score_within_005",
    ),
    "session_plateau_shape": (
        "session_count", "session_max_top", "session_max_second", "session_max_gap",
        "top_session_pairs", "top_session_chars", "top_session_score_mean",
        "top_session_score_std", "top_session_score_range", "best_pair_source_position",
    ),
    "rank_disagreement": (
        "score_spearman", "rank_displacement_mean", "rank_displacement_max",
        "top10_overlap", "top25_overlap", "top50_overlap",
    ),
    "packed_set_contrast": (
        "pair_selected_count", "session_selected_count", "selected_count_delta",
        "pair_packed_chars", "session_packed_chars", "packed_char_delta",
        "pair_slack", "session_slack", "pair_sessions_touched", "session_sessions_touched",
        "session_touch_delta", "selected_jaccard", "pair_only_count", "session_only_count",
        "pair_only_chars", "session_only_chars", "pair_selected_score_mean",
        "session_selected_score_mean", "pair_only_score_mean", "session_only_score_mean",
        "pair_unselected_score_mean", "session_unselected_score_mean",
    ),
    "budget_frontier": (
        "pair_selected_score_min", "session_selected_score_min", "pair_unselected_score_max",
        "session_unselected_score_max", "pair_frontier_margin", "session_frontier_margin",
    ),
}
FEATURES = tuple(name for family in FEATURE_FAMILIES.values() for name in family)


class AnatomyFeatureError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def _session_keys(conversation: Mapping[str, Any]) -> list[str]:
    found = []
    for key in conversation:
        match = _SESSION.fullmatch(key)
        if match:
            found.append((int(match.group(1)), key))
    return [key for _, key in sorted(found)]


def load_blind_cases(dataset_path: Path) -> list[dict[str, Any]]:
    if dataset_path.stat().st_size != DATASET_BYTES or sha256_file(dataset_path) != DATASET_SHA256:
        raise AnatomyFeatureError("LoCoMo dataset differs from the NF-004 lock")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    selected = [row for row in raw if row.get("sample_id") in HOLDOUT_IDS]
    if {row["sample_id"] for row in selected} != HOLDOUT_IDS:
        raise AnatomyFeatureError("NF-004 holdout conversations are incomplete")
    cases = []
    seen_keys: set[str] = set()
    for row in sorted(selected, key=lambda value: value["sample_id"]):
        candidates = []
        for session_order, session_id in enumerate(_session_keys(row["conversation"])):
            turns = row["conversation"][session_id]
            for pair_order, start in enumerate(range(0, len(turns), 2)):
                members = turns[start : start + 2]
                dialogue_ids = [str(turn["dia_id"]) for turn in members]
                text = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in members)
                candidates.append(Candidate(
                    identity=_identity(str(row["sample_id"]), session_id, *dialogue_ids, text),
                    session_identity=session_id,
                    session_order=session_order,
                    pair_order=pair_order,
                    text=text,
                    chars=len(text),
                ))
        questions = []
        occurrences: defaultdict[str, int] = defaultdict(int)
        for source_index, qa in enumerate(row["qa"]):
            canonical = json.dumps(qa, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            key = _identity(str(row["sample_id"]), canonical)
            ordinal = occurrences[key]
            occurrences[key] += 1
            if ordinal == 0:
                if key in seen_keys:
                    raise AnatomyFeatureError("Duplicate canonical question key")
                seen_keys.add(key)
            questions.append({
                "comparison_key": key,
                "duplicate_ordinal": ordinal,
                "sample_id": str(row["sample_id"]),
                "source_index": source_index,
                "text": str(qa["question"]),
            })
        cases.append({"sample_id": str(row["sample_id"]), "candidates": candidates, "questions": questions})
    return cases


def _rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0
        start = end
    return ranks


def _spearman(left: np.ndarray, right: np.ndarray) -> float:
    a, b = _rankdata(left), _rankdata(right)
    if float(np.std(a)) == 0.0 or float(np.std(b)) == 0.0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _mean(values: Sequence[float]) -> float:
    return float(np.mean(values)) if len(values) else 0.0


def feature_row(
    question: Mapping[str, Any], candidates: Sequence[Candidate], scores: np.ndarray,
    session_order: Sequence[int], pair_order: Sequence[int],
) -> dict[str, Any]:
    if len(candidates) < 2:
        raise AnatomyFeatureError("NF-004 case unexpectedly has fewer than two candidates")
    session_delivery = pack(candidates, session_order, BUDGET)
    pair_delivery = pack(candidates, pair_order, BUDGET)
    id_to_index = {candidate.identity: index for index, candidate in enumerate(candidates)}
    sessions: defaultdict[str, list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        sessions[candidate.session_identity].append(index)
    session_max = {key: max(float(scores[index]) for index in members) for key, members in sessions.items()}
    inherited = np.asarray([session_max[candidate.session_identity] for candidate in candidates])
    ordered_session_max = sorted(session_max.values(), reverse=True)
    top_session = max(session_max, key=lambda key: (session_max[key], -candidates[sessions[key][0]].session_order))
    top_members = sessions[top_session]
    best_index = max(top_members, key=lambda index: (float(scores[index]), -candidates[index].pair_order))
    session_positions = np.empty(len(candidates), dtype=int)
    pair_positions = np.empty(len(candidates), dtype=int)
    for position, index in enumerate(session_order):
        session_positions[index] = position
    for position, index in enumerate(pair_order):
        pair_positions[index] = position
    displacement = np.abs(session_positions - pair_positions)
    pair_set, session_set = set(pair_delivery.selected), set(session_delivery.selected)
    pair_only, session_only = pair_set - session_set, session_set - pair_set

    def values(chosen: set[str]) -> list[float]:
        return [float(scores[id_to_index[item]]) for item in chosen]

    def chars(chosen: set[str]) -> int:
        return sum(candidates[id_to_index[item]].chars for item in chosen)

    def sessions_touched(chosen: set[str]) -> int:
        return len({candidates[id_to_index[item]].session_identity for item in chosen})

    def frontier(chosen: set[str]) -> tuple[float, float, float]:
        selected = values(chosen)
        unselected = values(set(id_to_index) - chosen)
        selected_min = min(selected) if selected else 0.0
        unselected_max = max(unselected) if unselected else selected_min
        return selected_min, unselected_max, selected_min - unselected_max

    pair_min, pair_unselected_max, pair_margin = frontier(pair_set)
    session_min, session_unselected_max, session_margin = frontier(session_set)
    words = [word.lower() for word in _WORD.findall(str(question["text"]))]
    score_ordered = np.sort(scores)[::-1]
    maximum = float(score_ordered[0])
    row: dict[str, Any] = {
        "comparison_key": question["comparison_key"],
        "duplicate_ordinal": int(question["duplicate_ordinal"]),
        "sample_id": question["sample_id"],
        "source_index": int(question["source_index"]),
        "pair_payload_sha256": _identity(*pair_delivery.selected),
        "session_payload_sha256": _identity(*session_delivery.selected),
        "query_chars": len(str(question["text"])),
        "query_words": len(words),
        "query_unique_fraction": len(set(words)) / len(words) if words else 0.0,
        "query_digits": sum(character.isdigit() for character in str(question["text"])),
        "query_question_marks": str(question["text"]).count("?"),
        "score_max": maximum,
        "score_second": float(score_ordered[1]),
        "score_top_gap": maximum - float(score_ordered[1]),
        "score_mean": float(np.mean(scores)),
        "score_std": float(np.std(scores)),
        "score_p90_p50": float(np.percentile(scores, 90) - np.percentile(scores, 50)),
        "score_within_001": int(np.sum(scores >= maximum - 0.01)),
        "score_within_003": int(np.sum(scores >= maximum - 0.03)),
        "score_within_005": int(np.sum(scores >= maximum - 0.05)),
        "session_count": len(sessions),
        "session_max_top": float(ordered_session_max[0]),
        "session_max_second": float(ordered_session_max[1]),
        "session_max_gap": float(ordered_session_max[0] - ordered_session_max[1]),
        "top_session_pairs": len(top_members),
        "top_session_chars": sum(candidates[index].chars for index in top_members),
        "top_session_score_mean": _mean([scores[index] for index in top_members]),
        "top_session_score_std": float(np.std([scores[index] for index in top_members])),
        "top_session_score_range": float(max(scores[index] for index in top_members) - min(scores[index] for index in top_members)),
        "best_pair_source_position": candidates[best_index].pair_order + 1,
        "score_spearman": _spearman(scores, inherited),
        "rank_displacement_mean": float(np.mean(displacement)),
        "rank_displacement_max": int(np.max(displacement)),
        "pair_selected_count": len(pair_set),
        "session_selected_count": len(session_set),
        "selected_count_delta": len(pair_set) - len(session_set),
        "pair_packed_chars": pair_delivery.packed_chars,
        "session_packed_chars": session_delivery.packed_chars,
        "packed_char_delta": pair_delivery.packed_chars - session_delivery.packed_chars,
        "pair_slack": BUDGET - pair_delivery.packed_chars,
        "session_slack": BUDGET - session_delivery.packed_chars,
        "pair_sessions_touched": sessions_touched(pair_set),
        "session_sessions_touched": sessions_touched(session_set),
        "session_touch_delta": sessions_touched(pair_set) - sessions_touched(session_set),
        "selected_jaccard": len(pair_set & session_set) / len(pair_set | session_set),
        "pair_only_count": len(pair_only),
        "session_only_count": len(session_only),
        "pair_only_chars": chars(pair_only),
        "session_only_chars": chars(session_only),
        "pair_selected_score_mean": _mean(values(pair_set)),
        "session_selected_score_mean": _mean(values(session_set)),
        "pair_only_score_mean": _mean(values(pair_only)),
        "session_only_score_mean": _mean(values(session_only)),
        "pair_unselected_score_mean": _mean(values(set(id_to_index) - pair_set)),
        "session_unselected_score_mean": _mean(values(set(id_to_index) - session_set)),
        "pair_selected_score_min": pair_min,
        "session_selected_score_min": session_min,
        "pair_unselected_score_max": pair_unselected_max,
        "session_unselected_score_max": session_unselected_max,
        "pair_frontier_margin": pair_margin,
        "session_frontier_margin": session_margin,
    }
    for size in (10, 25, 50):
        actual = min(size, len(candidates))
        row[f"top{size}_overlap"] = len(set(pair_order[:actual]) & set(session_order[:actual])) / actual
    if not all(math.isfinite(float(row[name])) for name in FEATURES):
        raise AnatomyFeatureError("Nonfinite evidence-blind feature")
    return row


def extract_features(dataset_path: Path, cache_path: Path, manifest_path: Path, output_path: Path) -> dict[str, Any]:
    from episodic import EmbeddingCache

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache_record = manifest["cache"]
    cases = load_blind_cases(dataset_path)
    rows = []
    with EmbeddingCache(
        cache_path, mode="reuse", expected_file_sha256=cache_record["file_sha256"],
        expected_content_sha256=cache_record["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDING_SHA256,
    ) as cache:
        for case in cases:
            candidates = case["candidates"]
            matrix = np.vstack([np.asarray(cache(candidate.text), dtype=np.float32) for candidate in candidates])
            norms = np.linalg.norm(matrix, axis=1)
            for question in case["questions"]:
                query = np.asarray(cache(question["text"]), dtype=np.float32)
                scores = (matrix / norms[:, None]) @ (query / np.linalg.norm(query))
                session_order, pair_order = ranking_orders(candidates, matrix, query)
                rows.append(feature_row(question, candidates, scores, session_order, pair_order))
        reuse = cache.record()
    rows.sort(key=lambda row: (row["comparison_key"], row["duplicate_ordinal"]))
    if len(rows) != 1_104 or len({row["comparison_key"] for row in rows if row["duplicate_ordinal"] == 0}) != 1_104:
        raise AnatomyFeatureError("Blind feature population differs from NF-004")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "rows": len(rows), "conversations": len(cases), "features": len(FEATURES),
        "feature_sha256": sha256_file(output_path), "dataset_sha256": sha256_file(dataset_path),
        "cache_file_sha256": reuse["file_sha256"], "cache_content_sha256": reuse["content_sha256"],
        "cache_hits": reuse["hits"], "cache_misses": reuse["misses"],
        "embedding_calls": 0, "model_calls": 0,
    }


def run_preflight(dataset_path: Path, cache_path: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_path = output_dir / "features.csv"
    first = extract_features(dataset_path, cache_path, manifest_path, feature_path)
    with tempfile.TemporaryDirectory(prefix="nf004-anatomy-") as directory:
        replay_path = Path(directory) / "features.csv"
        second = extract_features(dataset_path, cache_path, manifest_path, replay_path)
        replay_identical = feature_path.read_bytes() == replay_path.read_bytes()
    source = Path(__file__).read_text(encoding="utf-8").lower()
    forbidden_tokens = ("nf004_measurement", "g6_holdout_outcomes", '["category"]', '["answer"]', '["evidence"]')
    scanned_source = "\n".join(
        line for line in source.splitlines() if "forbidden_tokens =" not in line
    )
    leakage_clean = not any(token in scanned_source for token in forbidden_tokens)
    result = {
        "schema": "nf004-item-anatomy-preflight-v1",
        "status": "PASS" if replay_identical and leakage_clean and first["cache_misses"] == 0 else "FAIL",
        "feature_sha256": first["feature_sha256"],
        "feature": first,
        "replay_feature_sha256": second["feature_sha256"],
        "replay_byte_identical": replay_identical,
        "leakage_scan_clean": leakage_clean,
        "forbidden_tokens": list(forbidden_tokens),
        "historical_payload_limitation": "NF-004 G6 retained metrics, not selected candidate identities; see Amendment 001",
        "calls": {"embedding": 0, "model": 0, "cache_misses": first["cache_misses"] + second["cache_misses"]},
    }
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "PASS":
        raise AnatomyFeatureError("Item-anatomy preflight failed")
    return result


__all__ = ["AnatomyFeatureError", "FEATURES", "FEATURE_FAMILIES", "extract_features", "feature_row", "run_preflight", "sha256_file"]
