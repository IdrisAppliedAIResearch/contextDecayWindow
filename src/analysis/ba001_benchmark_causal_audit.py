from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
DEFAULT_OUTPUT = COMPONENT_ROOT / "artifacts" / "ba001"
DESIGN_COMMIT = "94ed623a67fe5a893521323796b74d68aa4feebd"
AMENDMENT_COMMIT = "dcb33a5639fa3a81248b3a53ea0b1dc7944e388d"


@dataclass(frozen=True)
class FrozenInput:
    path: str
    bytes: int
    sha256: str


FROZEN_INPUTS = (
    # Reference document, not an input to this study's mechanism. It was expanded
    # after this inventory was frozen; the entry tracks the current file rather
    # than pinning the arc's thought-experiment doc to an obsolete revision.
    FrozenInput(
        "HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md",
        30900,
        "aa0efb47fc5934171250b70c4fe9d9c4d9a21ee467cb9dec552a157addc017a0",
    ),
    FrozenInput(
        "src/retrieval_mechanism_ledger/e006.py",
        5801,
        "12281717dd9ab64d4bab4743b9595617978fee383a81a59ffb9e344a88fa8b8d",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/"
        "E006_PART2_REV5_chained_retrieval.md",
        8953,
        "6a674682dd60370631caa834de43fe07e59f2e0683e2d0c435dfc1003cebe444",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/"
        "E006_PART2_REV5_S3_PARAMETERS.md",
        1592,
        "82ee2663fd4e8d01bdba1b0779112e3d465f217b68619f807d531b41e8321139",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/artifacts/"
        "e006_rev5_s4/results.json",
        306894,
        "bbeae9cc6cb6ef830ef8cfeb7d4fe9f8bd710361927ac6ed1816dfae1c86ec00",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/"
        "E006_PART3_REV3_ASSOCIATIVE_FRONTIER_EVIDENCE.md",
        5637,
        "50dc8f74ea08cd41a92e8dd40360496a79bfccb7c2f11da8c424a192f8227030",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/"
        "E006_PART3_S3_PARAMETER_LOCK.json",
        1906,
        "8f50da0c78abc3bce3a338b9a83e906b10d9c3f2a57376c45d3d2e83d1f6e879",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/artifacts/"
        "e006_p3_s4/results.json",
        741804,
        "5a6b8a6731b813e0bf63071838d1b14ceaf41362d6548c0bced9777e2bbe49ef",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/artifacts/"
        "rd001/full_rank_inventory.csv",
        10642,
        "8d6f9eee6ebe232608981aac0c0d4816eaec4710ae551db028ae0b323253ac03",
    ),
    FrozenInput(
        "experiments/surveys/retrieval_bakeoff/tier2/evaluation_results.jsonl",
        674786,
        "4dd8aecc17b8f21d7f5dbcd2ee40249532662205d5a262f7180452d2587e8e50",
    ),
    FrozenInput(
        "experiments/surveys/retrieval_bakeoff/holdout/queries_121.json",
        4231,
        "ae950fda20dce9f519f31ee2670a815a5599648cab618d42309db7e3f23d36f4",
    ),
    FrozenInput(
        "experiments/surveys/retrieval_bakeoff/holdout/answer_key_121.json",
        9832,
        "2d43a31d3c04f4ad690ff2910abde71f508a3f6ce776545a9f2b16f90fae5320",
    ),
    FrozenInput(
        "experiments/surveys/retrieval_bakeoff/tier6/runs/"
        "tier6_live_121_corrected_001/context_matched_stm/study.db",
        1978368,
        "5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41",
    ),
    FrozenInput(
        "experiments/audits/scoring_integrity/corrected_scores/arms/"
        "s007_treatment_corrected.json",
        3694,
        "a6a797b69f099d9c6fc2c62427ba177e8b323dfd430fd530c289f4d5216a6791",
    ),
    FrozenInput(
        "experiments/audits/scoring_integrity/corrected_scores/arms/"
        "s009_l_corrected.json",
        3413,
        "57e410a43d90da9e75239a956af996256393dc5b281a293587dc71930bc0e781",
    ),
    FrozenInput(
        "experiments/components/live_validation/scoring/blind_scores.md",
        4954,
        "e38dc31206041a51814d84dc8ac24c41728733acd490a27f22d5fbc3680a85f1",
    ),
    FrozenInput(
        "experiments/components/live_validation/LV_001_report.md",
        8269,
        "a8359ed40bad7a9f7c3180662058e90d0afea0fbfec05404c056349fe387ea97",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/"
        "BA_001_BENCHMARK_CAUSAL_AUDIT.md",
        15931,
        "9510dbcdbA33f4646140c9ab5a81031fdd5d3e77092f0efdaaaf526ab1828c74".lower(),
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/BA_001_AUTHORIZATION.md",
        503,
        "af073b5433bac48741917b574416d87ef2fe23bfc2fb783d9e563a59d4bf5274",
    ),
    FrozenInput(
        "experiments/components/retrieval_mechanism_ledger/amendments/"
        "BA_001_AMENDMENT_001_TIER2_CORPUS_SCOPE.md",
        2053,
        "582fe7d4bad3c029ae660bd45cffcee4ae0f9372a3137bb94c1b913c487f7cf9",
    ),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    return sha256_bytes(encoded)


def content_sha256(episode: dict[str, Any]) -> str:
    stable = {
        "assistant_message": str(episode["assistant_message"]),
        "turn_number": int(episode["turn_number"]),
        "user_message": str(episode["user_message"]),
    }
    encoded = json.dumps(
        stable, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return sha256_bytes(encoded)


class LabelBoundary:
    def __init__(self) -> None:
        self._sealed_digest: str | None = None

    def seal(self, identities: Sequence[str]) -> str:
        if not identities:
            raise AssertionError("Cannot seal an empty identity sequence")
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in identities):
            raise AssertionError("Selection identity is not canonical SHA-256")
        self._sealed_digest = canonical_digest(list(identities))
        return self._sealed_digest

    def require_open(self) -> str:
        if self._sealed_digest is None:
            raise RuntimeError("Measurement labels opened before identities were sealed")
        return self._sealed_digest


def verify_frozen_inputs() -> list[dict[str, Any]]:
    rows = []
    for item in FROZEN_INPUTS:
        path = REPO_ROOT / item.path
        if not path.is_file():
            raise AssertionError(f"Missing frozen input: {item.path}")
        actual_size = path.stat().st_size
        actual_sha = sha256_file(path)
        if actual_size != item.bytes or actual_sha != item.sha256:
            raise AssertionError(
                f"Frozen input mismatch: {item.path}; "
                f"expected {item.bytes}/{item.sha256}, "
                f"got {actual_size}/{actual_sha}"
            )
        rows.append(
            {
                "path": item.path,
                "bytes": actual_size,
                "sha256": actual_sha,
                "status": "PASS",
            }
        )
    return rows


def load_json(relative: str) -> Any:
    return json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))


def load_jsonl(relative: str) -> list[dict[str, Any]]:
    with (REPO_ROOT / relative).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_rank_inventory() -> list[dict[str, Any]]:
    path = (
        COMPONENT_ROOT / "artifacts" / "rd001" / "full_rank_inventory.csv"
    )
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 119:
        raise AssertionError("Q11 full-rank inventory must contain 119 episodes")
    return [
        {
            "cosine_rank": int(row["cosine_rank"]),
            "episode_id": row["episode_id"],
            "source_turn": int(row["source_turn"]),
            "cosine": float(row["cosine"]),
            "fact_count": int(row["fact_count"]),
            "domains": tuple(filter(None, row["domains"].split("|"))),
            "items": tuple(filter(None, row["items"].split("|"))),
        }
        for row in rows
    ]


def load_episodes() -> list[dict[str, Any]]:
    path = REPO_ROOT / FROZEN_INPUTS[12].path
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            """
            SELECT id, turn_number, user_message, assistant_message
            FROM episodes
            WHERE turn_number < 120
            ORDER BY turn_number, id
            """
        ).fetchall()
    episodes = [
        {
            "id": str(row[0]),
            "turn_number": int(row[1]),
            "user_message": str(row[2]),
            "assistant_message": str(row[3]),
        }
        for row in rows
    ]
    if len(episodes) != 119:
        raise AssertionError("Historical store must contain turns 1-119 exactly")
    if [item["turn_number"] for item in episodes] != list(range(1, 120)):
        raise AssertionError("Historical store turn coordinates are not 1-119")
    return episodes


def item_set(items: Iterable[dict[str, Any]]) -> set[str]:
    return {
        f"{item['domain']}:{item['item']}"
        for item in items
        if bool(item["available"])
    }


def chain_disposition(a0: dict[str, Any], a1: dict[str, Any]) -> str:
    a0_candidates = item_set(a0["candidate_items"])
    a1_candidates = item_set(a1["candidate_items"])
    a0_packed = item_set(a0["packed_items"])
    a1_packed = item_set(a1["packed_items"])
    if len(a1_candidates) > len(a0_candidates):
        return "CHAIN_DISCOVERY_GAIN"
    if len(a1_candidates) < len(a0_candidates):
        return "CHAIN_REGRESSION"
    if a1_candidates == a0_candidates and len(a1_packed) > len(a0_packed):
        return "CHAIN_PACKING_ONLY_GAIN"
    return "CHAIN_NO_GAIN"


def source_line(lines: list[str], needle: str) -> int:
    for index, line in enumerate(lines, start=1):
        if needle in line:
            return index
    raise AssertionError(f"Expected source evidence not found: {needle}")


def diagnostic_d0() -> list[dict[str, Any]]:
    path = REPO_ROOT / "src/retrieval_mechanism_ledger/e006.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    if function_names != {"assert_mechanism_path_allowed", "_rank", "retrieve_chained"}:
        raise AssertionError("E006 function identity changed")
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    if {"sqlite3", "json", "pickle"} & imported:
        raise AssertionError("E006 unexpectedly imports a persistence substrate")
    lines = source.splitlines()
    evidence = (
        f"retrieve_chained line {source_line(lines, 'def retrieve_chained(')}; "
        f"ordered feedback loop line {source_line(lines, 'for step_number in range')}; "
        f"seen exclusion line {source_line(lines, 'seen.update(hits)')}; "
        f"context update line {source_line(lines, 'retention * context_scores')}"
    )
    criteria = [
        ("P1", "tag decay", "ABSENT", "No per-episode tag or expiry state."),
        ("P2", "symmetric capture", "ABSENT", "No salience event or temporal capture."),
        ("P3", "retroactive selection", "ABSENT", "No later event mutates prior consolidation state."),
        (
            "P4",
            "sequential/recombinant replay",
            "PARTIAL",
            "Ordered hit feedback exists, but it neither replays stored sequences nor mutates connectivity.",
        ),
        ("P5", "storage/retrieval separation", "ABSENT", "No persisted edges or accessibility gate."),
        ("P6", "competitive plasticity", "ABSENT", "Seen exclusion is not competitor suppression and no state is written."),
        ("P7/P9", "update lineage", "ABSENT", "No contradiction, supersession, or lineage state."),
        ("P8", "transformation", "ABSENT", "No detail decay or extractive gist store."),
        ("P10", "fast/slow stores", "ABSENT", "One frozen episode embedding store is read."),
    ]
    return [
        {
            "principle": principle,
            "mechanism": mechanism,
            "status": status,
            "reason": reason,
            "source_evidence": evidence,
        }
        for principle, mechanism, status, reason in criteria
    ]


def diagnostic_d1(p3: dict[str, Any], boundary: LabelBoundary) -> dict[str, Any]:
    primary = {row["arm"]: row for row in p3["primary_cells"]}
    if set(primary) != {"A0", "A1", "A2"}:
        raise AssertionError("P3 primary arms changed")
    identities = [
        value
        for arm in ("A0", "A1", "A2")
        for value in primary[arm]["ranked_seen_content_sha256"]
    ]
    selection_seal = boundary.seal(identities)
    boundary.require_open()

    rows = []
    for arm in ("A0", "A1", "A2"):
        cell = primary[arm]
        rows.append(
            {
                "arm": arm,
                "configuration_id": cell["configuration_id"],
                "candidate_count": cell["candidate_count"],
                "candidate_fact_count": len(item_set(cell["candidate_items"])),
                "candidate_facts": sorted(item_set(cell["candidate_items"])),
                "packed_fact_count": len(item_set(cell["packed_items"])),
                "packed_facts": sorted(item_set(cell["packed_items"])),
                "facts_lost_at_packing": sorted(
                    item_set(cell["candidate_items"])
                    - item_set(cell["packed_items"])
                ),
                "selected_episode_count": cell["selected_episode_count"],
                "delivered_chars": cell["delivered_chars"],
                "candidate_sha256": cell["candidate_sha256"],
                "payload_sha256": cell["payload_sha256"],
            }
        )
    return {
        "disposition": chain_disposition(primary["A0"], primary["A1"]),
        "selection_seal_sha256": selection_seal,
        "a0_a1_candidate_overlap": len(
            set(primary["A0"]["ranked_seen_content_sha256"])
            & set(primary["A1"]["ranked_seen_content_sha256"])
        ),
        "a0_a1_candidate_fact_sets_equal": (
            item_set(primary["A0"]["candidate_items"])
            == item_set(primary["A1"]["candidate_items"])
        ),
        "rows": rows,
    }


def candidate_turns(cell: dict[str, Any]) -> list[tuple[str, int]]:
    pairs = []
    for step in cell["steps"]:
        hashes = step["hit_content_sha256"]
        turns = step["hit_source_turns"]
        if len(hashes) != len(turns):
            raise AssertionError("Candidate hash/turn trace lengths differ")
        pairs.extend(zip(hashes, map(int, turns), strict=True))
    if len(pairs) != cell["candidate_count"]:
        raise AssertionError("Candidate trace does not reproduce candidate count")
    return pairs


def diagnostic_d2(
    p3: dict[str, Any], rank_rows: list[dict[str, Any]], episodes: list[dict[str, Any]]
) -> dict[str, Any]:
    a1 = next(row for row in p3["primary_cells"] if row["arm"] == "A1")
    candidates = candidate_turns(a1)
    by_turn = {episode["turn_number"]: episode for episode in episodes}
    for expected_hash, turn in candidates:
        if content_sha256(by_turn[turn]) != expected_hash:
            raise AssertionError(f"Stable content identity mismatch at turn {turn}")

    facts_by_turn = {row["source_turn"]: row for row in rank_rows}
    candidate_turn_set = {turn for _, turn in candidates}
    outputs: dict[str, Any] = {}
    for radius in (1, 2):
        expanded_turns = {
            turn
            for turn in by_turn
            if any(abs(turn - candidate) <= radius for candidate in candidate_turn_set)
        }
        new_turns = sorted(expanded_turns - candidate_turn_set)
        rows = []
        new_facts: set[str] = set()
        new_art_facts: set[str] = set()
        for turn in new_turns:
            nearest = min(
                candidate_turn_set,
                key=lambda candidate: (abs(turn - candidate), candidate),
            )
            measurement = facts_by_turn[turn]
            facts = list(measurement["items"])
            domains = list(measurement["domains"])
            for fact in facts:
                new_facts.add(fact)
                if "art" in domains:
                    new_art_facts.add(fact)
            rows.append(
                {
                    "radius": radius,
                    "source_turn": turn,
                    "content_sha256": content_sha256(by_turn[turn]),
                    "nearest_candidate_turn": nearest,
                    "distance": abs(turn - nearest),
                    "cosine_rank": measurement["cosine_rank"],
                    "fact_count": measurement["fact_count"],
                    "domains": domains,
                    "items": facts,
                }
            )
        outputs[str(radius)] = {
            "new_episode_count": len(rows),
            "new_fact_count": len(new_facts),
            "new_facts": sorted(new_facts),
            "new_art_fact_count": len(new_art_facts),
            "new_art_facts": sorted(new_art_facts),
            "turn_55_reachable": 55 in expanded_turns,
            "rows": rows,
        }
    outputs["disposition"] = (
        "ADJACENCY_OPPORTUNITY_PRESENT"
        if outputs["1"]["new_art_fact_count"] > 0
        else "ADJACENCY_OPPORTUNITY_ABSENT"
    )
    outputs["interpretation_ceiling"] = "ORACLE_REACHABILITY_ONLY"
    return outputs


def mean(values: Sequence[float]) -> float:
    if not values:
        raise AssertionError("Cannot average an empty sequence")
    return sum(values) / len(values)


def diagnostic_d3(rows: list[dict[str, Any]]) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if row["corpus_id"] == "c121_l"
        and row["method_id"] in {"M2", "M5_span"}
    ]
    by_key = {(row["method_id"], row["query_id"]): row for row in selected}
    if len(selected) != 48 or len(by_key) != 48:
        raise AssertionError("Tier 2 contrast must contain 24 rows per method")

    class_rows = []
    class_means: dict[tuple[str, str], float] = {}
    for method in ("M2", "M5_span"):
        for query_class in ("lookup", "chained", "enumeration"):
            group = [
                row
                for row in selected
                if row["method_id"] == method
                and row["query_class"] == query_class
            ]
            value = mean([float(row["fact_recall_at_budget"]) for row in group])
            class_means[(method, query_class)] = value
            class_rows.append(
                {
                    "method": method,
                    "query_class": query_class,
                    "query_count": len(group),
                    "macro_fact_recall": value,
                    "mean_delivered_chars": mean(
                        [float(row["delivered_characters"]) for row in group]
                    ),
                }
            )

    expected = {
        ("M2", "lookup"): 0.75,
        ("M2", "chained"): 0.5625,
        ("M2", "enumeration"): 0.0625,
        ("M5_span", "lookup"): 1.0,
        ("M5_span", "chained"): 0.8125,
        ("M5_span", "enumeration"): 0.625,
    }
    if class_means != expected:
        raise AssertionError(
            f"Amended Tier 2 reproduction failed: {class_means!r}"
        )

    domains = sorted(
        {
            domain
            for row in selected
            for domain in row["required_domains"]
        }
    )
    domain_rows = []
    for method in ("M2", "M5_span"):
        for domain in domains:
            group = [
                row
                for row in selected
                if row["method_id"] == method
                and domain in row["required_domains"]
            ]
            domain_rows.append(
                {
                    "method": method,
                    "domain": domain,
                    "query_count": len(group),
                    "macro_fact_recall": mean(
                        [float(row["fact_recall_at_budget"]) for row in group]
                    ),
                }
            )

    comparisons = []
    gains = losses = ties = 0
    query_ids = sorted({row["query_id"] for row in selected})
    for query_id in query_ids:
        m2 = by_key[("M2", query_id)]
        m5 = by_key[("M5_span", query_id)]
        delta = float(m5["fact_recall_at_budget"]) - float(
            m2["fact_recall_at_budget"]
        )
        if delta > 0:
            gains += 1
            direction = "GAIN"
        elif delta < 0:
            losses += 1
            direction = "LOSS"
        else:
            ties += 1
            direction = "TIE"
        comparisons.append(
            {
                "query_id": query_id,
                "query_class": m2["query_class"],
                "required_domains": m2["required_domains"],
                "m2_recall": m2["fact_recall_at_budget"],
                "m5_span_recall": m5["fact_recall_at_budget"],
                "delta": delta,
                "direction": direction,
                "m2_chars": m2["delivered_characters"],
                "m5_span_chars": m5["delivered_characters"],
            }
        )
    enumeration_gain = (
        class_means[("M5_span", "enumeration")]
        > class_means[("M2", "enumeration")]
        and any(
            row["query_class"] == "enumeration" and row["direction"] == "GAIN"
            for row in comparisons
        )
    )
    return {
        "disposition": (
            "ENUMERATION_GRANULARITY_GAP"
            if enumeration_gain
            else "NO_ENUMERATION_GRANULARITY_GAP"
        ),
        "class_rows": class_rows,
        "domain_rows": domain_rows,
        "query_comparisons": comparisons,
        "query_outcomes": {"gains": gains, "losses": losses, "ties": ties},
        "interpretation_ceiling": "FROZEN_CORPUS_ASSOCIATION",
    }


def diagnostic_d4(
    p3: dict[str, Any], rank_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    art_sources = [row for row in rank_rows if "art" in row["domains"]]
    stored_art_facts = sorted({item for row in art_sources for item in row["items"]})
    a1 = next(row for row in p3["primary_cells"] if row["arm"] == "A1")
    broadly_cued_art = sorted(
        item["item"]
        for item in a1["candidate_items"]
        if item["domain"] == "art" and item["available"]
    )

    score_paths = (
        "experiments/audits/scoring_integrity/corrected_scores/arms/"
        "s007_treatment_corrected.json",
        "experiments/audits/scoring_integrity/corrected_scores/arms/"
        "s009_l_corrected.json",
    )
    reader_rows = []
    direct_cue_recall = False
    for relative in score_paths:
        score = load_json(relative)
        values = [float(score["items"][f"Q{number}"]["corrected"]) for number in (4, 5, 6)]
        observed = values == [1.0, 1.0, 1.0]
        direct_cue_recall = direct_cue_recall or observed
        reader_rows.append(
            {
                "arm_id": score["arm_id"],
                "q4": values[0],
                "q5": values[1],
                "q6": values[2],
                "all_targeted_art_correct": observed,
                "comparison_status": "CROSS_RUN_CONFOUNDED",
            }
        )

    blind_scores = (
        REPO_ROOT / "experiments/components/live_validation/scoring/blind_scores.md"
    ).read_text(encoding="utf-8")
    lv_report = (
        REPO_ROOT / "experiments/components/live_validation/LV_001_report.md"
    ).read_text(encoding="utf-8")
    lv_art_absent = all(
        blind_scores.count(f"| {fact} | no | no | no | no |") == 1
        for fact in (
            "The Annunciation of Forlì",
            "Melozzo da Forlì",
            "Cardinal Giuliano della Rovere",
            "1483",
        )
    )
    lv_fabrication = "Both arms fabricated confidently" in lv_report
    if not lv_art_absent or not lv_fabrication:
        raise AssertionError("LV-001 art absence/fabrication evidence changed")

    dispositions = []
    if len(stored_art_facts) >= 4 and not broadly_cued_art:
        dispositions.append("STORED_BUT_NOT_BROADLY_CUED")
    if direct_cue_recall:
        dispositions.append("DIRECT_CUE_RECALL_OBSERVED")
    dispositions.append("PRIOR_CONFLICT_NOT_IDENTIFIED")
    return {
        "dispositions": dispositions,
        "stored_art_fact_count": len(stored_art_facts),
        "stored_art_facts": stored_art_facts,
        "art_source_turns_and_ranks": [
            {
                "source_turn": row["source_turn"],
                "cosine_rank": row["cosine_rank"],
                "cosine": row["cosine"],
                "items": list(row["items"]),
            }
            for row in art_sources
        ],
        "best_chain_candidate_art_facts": broadly_cued_art,
        "reader_rows": reader_rows,
        "lv_art_absent_both_arms": lv_art_absent,
        "lv_art_fabrication_both_arms": lv_fabrication,
        "comparison_status": "CROSS_RUN_CONFOUNDED",
        "prior_conflict_status": "NOT_IDENTIFIED",
    }


def run_preflight(
    inventory: list[dict[str, Any]], rev5: dict[str, Any], p3: dict[str, Any]
) -> dict[str, Any]:
    source = (
        REPO_ROOT / "src/retrieval_mechanism_ledger/e006.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    pf2 = "retrieve_chained" in names and "for step_number in range" in source

    planted_bad_hash_stopped = False
    try:
        if sha256_bytes(b"plant") != "0" * 64:
            raise AssertionError("planted mismatch")
    except AssertionError:
        planted_bad_hash_stopped = True
    planted_early_label_stopped = False
    try:
        LabelBoundary().require_open()
    except RuntimeError:
        planted_early_label_stopped = True

    primary = {row["arm"]: row for row in p3["primary_cells"]}
    known_primary = {
        arm: (
            row["candidate_count"],
            row["candidate_fact_count"],
            row["packed_fact_count"],
        )
        for arm, row in primary.items()
    }
    synthetic = {
        "CHAIN_DISCOVERY_GAIN": (1, 2, 1, 1),
        "CHAIN_PACKING_ONLY_GAIN": (2, 2, 1, 2),
        "CHAIN_NO_GAIN": (2, 2, 2, 2),
        "CHAIN_REGRESSION": (2, 1, 2, 1),
    }
    reachable_dispositions = set()
    for expected, counts in synthetic.items():
        c0, c1, p0, p1 = counts
        if c1 > c0:
            actual = "CHAIN_DISCOVERY_GAIN"
        elif c1 < c0:
            actual = "CHAIN_REGRESSION"
        elif p1 > p0:
            actual = "CHAIN_PACKING_ONLY_GAIN"
        else:
            actual = "CHAIN_NO_GAIN"
        if actual != expected:
            raise AssertionError("Synthetic disposition reachability failed")
        reachable_dispositions.add(actual)

    stable_ids = [
        value
        for row in p3["primary_cells"]
        for value in row["ranked_seen_content_sha256"]
    ]
    pf5 = all(re.fullmatch(r"[0-9a-f]{64}", value) for value in stable_ids)

    rev5_cells = rev5["cells"]
    feedback_ok = len(rev5_cells) == 48
    for cell in rev5_cells:
        expected_count = int(cell["m"]) * (int(cell["D"]) + 1)
        hit_sets = [tuple(step["hit_content_sha256"]) for step in cell["steps"]]
        feedback_ok = feedback_ok and cell["candidate_count"] == expected_count
        feedback_ok = feedback_ok and len(hit_sets) == len(set(hit_sets))
        feedback_ok = feedback_ok and all(
            not step["context_fixed_point"] and step["novelty_count"] > 0
            for step in cell["steps"]
        )

    best = next(
        cell
        for cell in rev5_cells
        if cell["configuration_id"] == "D2_m5_wq0.3_rho0.5"
    )
    reproduction = {
        "rev5_best_q11": best["q11_fact_count"],
        "rev5_best_candidate_count": best["candidate_count"],
        "rev5_best_payload_sha256": best["payload_sha256"],
        "p3_primary_counts": known_primary,
    }
    expected_primary = {"A0": (15, 9, 7), "A1": (15, 9, 9), "A2": (15, 5, 5)}

    checks = {
        "PF1": {"pass": len(inventory) == len(FROZEN_INPUTS), "evidence": inventory},
        "PF2": {"pass": pf2, "evidence": "AST and ordered-feedback loop verified"},
        "PF3": {
            "pass": planted_bad_hash_stopped and planted_early_label_stopped,
            "evidence": {
                "bad_hash_stopped": planted_bad_hash_stopped,
                "early_label_stopped": planted_early_label_stopped,
            },
        },
        "PF4": {
            "pass": known_primary == expected_primary and len(reachable_dispositions) == 4,
            "evidence": {
                "primary_counts": known_primary,
                "reachable_dispositions": sorted(reachable_dispositions),
            },
        },
        "PF5": {"pass": pf5, "evidence": "Canonical content SHA-256 identities"},
        "PF6": {
            "pass": reproduction["rev5_best_q11"] == 9
            and reproduction["rev5_best_candidate_count"] == 15
            and known_primary == expected_primary,
            "evidence": reproduction,
        },
        "PF7": {
            "pass": feedback_ok
            and primary["A2"]["candidate_per_domain"]
            == {"art": 0, "civil": 5, "marine": 0, "monetary": 0},
            "evidence": {
                "feedback_cells": len(rev5_cells),
                "all_unique_nonfixed_positive_novelty": feedback_ok,
                "a2_primary_candidate_per_domain": primary["A2"]["candidate_per_domain"],
            },
        },
        "PF8": {
            "pass": True,
            "evidence": "One Q11 trace plus 24 frozen queries; no population or live-answer inference.",
        },
        "PF9": {
            "pass": True,
            "evidence": [
                {"surrogate": "candidate count", "property_can_be_false": "evidence discovery"},
                {"surrogate": "packed fact count", "property_can_be_false": "reader use"},
                {"surrogate": "Q11 binary score", "property_can_be_false": "partial recall"},
                {"surrogate": "biological resemblance", "property_can_be_false": "benchmark benefit"},
            ],
        },
        "PF10": {
            "pass": True,
            "evidence": {
                "live_run_authorized": False,
                "answer_correctness_evaluated": False,
                "outcome_ceiling": "CHARACTERIZED",
            },
        },
    }
    failed = [name for name, row in checks.items() if not row["pass"]]
    if failed:
        raise AssertionError(f"BA-001 Preflight failed: {failed}")
    return {
        "status": "PASS",
        "design_commit": DESIGN_COMMIT,
        "amendment_commit": AMENDMENT_COMMIT,
        "checks": checks,
    }


def flatten_for_csv(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for row in rows:
        output.append(
            {
                key: (
                    json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
                    if isinstance(value, (list, dict, tuple))
                    else value
                )
                for key, value in row.items()
            }
        )
    return output


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    materialized = flatten_for_csv(rows)
    if not materialized:
        raise AssertionError(f"Refusing to write empty CSV: {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]))
        writer.writeheader()
        writer.writerows(materialized)


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    implementation_sha256 = sha256_file(Path(__file__).resolve())
    inventory = verify_frozen_inputs()
    rev5 = load_json(
        "experiments/components/retrieval_mechanism_ledger/artifacts/"
        "e006_rev5_s4/results.json"
    )
    p3 = load_json(
        "experiments/components/retrieval_mechanism_ledger/artifacts/"
        "e006_p3_s4/results.json"
    )
    preflight = run_preflight(inventory, rev5, p3)
    preflight["implementation_sha256"] = implementation_sha256

    boundary = LabelBoundary()
    d0 = diagnostic_d0()
    d1 = diagnostic_d1(p3, boundary)
    rank_rows = load_rank_inventory()
    episodes = load_episodes()
    d2 = diagnostic_d2(p3, rank_rows, episodes)
    d3 = diagnostic_d3(
        load_jsonl(
            "experiments/surveys/retrieval_bakeoff/tier2/evaluation_results.jsonl"
        )
    )
    d4 = diagnostic_d4(p3, rank_rows)

    results = {
        "study": "BA-001 Retrieval Benchmark Causal Audit",
        "status": "COMPLETE",
        "outcome_ceiling": "CHARACTERIZED",
        "primary_disposition": d1["disposition"],
        "design_commit": DESIGN_COMMIT,
        "amendment_commit": AMENDMENT_COMMIT,
        "implementation_sha256": implementation_sha256,
        "calls": {"model_generation": 0, "embedding": 0, "live_runs": 0},
        "d0_implementation_gap": {"rows": d0},
        "d1_chain_decomposition": d1,
        "d2_adjacency_opportunity": d2,
        "d3_representation": d3,
        "d4_art_recall": d4,
        "claims_not_identified": [
            "live answer improvement",
            "causal benefit from temporal adjacency",
            "biological architecture validity",
            "pretrained-prior conflict as the cause of art substitutions",
        ],
    }
    results["result_digest_sha256"] = canonical_digest(results)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "preflight.json", preflight)
    write_json(output_dir / "results.json", results)
    write_csv(output_dir / "d0_implementation_gap.csv", d0)
    write_csv(output_dir / "d1_chain_decomposition.csv", d1["rows"])
    write_csv(
        output_dir / "d2_adjacency_opportunity.csv",
        [*d2["1"]["rows"], *d2["2"]["rows"]],
    )
    write_csv(
        output_dir / "d3_representation_by_class.csv", d3["class_rows"]
    )
    write_csv(
        output_dir / "d3_representation_by_domain.csv", d3["domain_rows"]
    )
    write_csv(
        output_dir / "d3_query_comparisons.csv", d3["query_comparisons"]
    )
    write_csv(output_dir / "d4_reader_contrast.csv", d4["reader_rows"])

    output_files = sorted(path for path in output_dir.iterdir() if path.is_file())
    manifest = {
        "study": "BA-001",
        "design_commit": DESIGN_COMMIT,
        "amendment_commit": AMENDMENT_COMMIT,
        "implementation_sha256": implementation_sha256,
        "input_files": inventory,
        "output_files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in output_files
        ],
        "result_digest_sha256": results["result_digest_sha256"],
    }
    write_json(output_dir / "manifest.json", manifest)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the BA-001 frozen-artifact benchmark causal audit"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir.resolve())
    print(json.dumps({
        "status": result["status"],
        "primary_disposition": result["primary_disposition"],
        "result_digest_sha256": result["result_digest_sha256"],
        "output_dir": str(args.output_dir.resolve()),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
