"""Joined mechanism decomposition for DA-002."""

from __future__ import annotations

import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da001_linked_context import ARMS, SEED_COUNTS
from analysis.da002_provenance import DA002Error
from analysis.nf004_anatomy_features import sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split


def _read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _write_gzip(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for row in rows:
                compressed.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "p10": None, "p50": None, "p90": None, "max": None}
    array = np.asarray(values, dtype=float)
    return {
        "n": len(values), "min": float(np.min(array)),
        "p10": float(np.percentile(array, 10)), "p50": float(np.percentile(array, 50)),
        "p90": float(np.percentile(array, 90)), "max": float(np.max(array)),
    }


def classify_trajectory(direct_complete: bool, states: Sequence[bool]) -> dict[str, Any]:
    active = [state != direct_complete for state in states]
    symbol = "L" if direct_complete else "G"
    sequence = "".join(symbol if value else "T" for value in active)
    transitions = [SEED_COUNTS[index] for index in range(1, len(active)) if active[index] != active[index - 1]]
    if not any(active):
        category = "ALWAYS_TIED"
        first = None
    else:
        first_index = active.index(True)
        first = SEED_COUNTS[first_index]
        if all(active[first_index:]):
            category = f"PERSISTENT_{'LOSS' if direct_complete else 'GAIN'}"
        elif sum(active[index] != active[index - 1] for index in range(1, len(active))) <= 2:
            category = "LOSS_THEN_RECOVER" if direct_complete else "GAIN_THEN_REVERT"
        else:
            category = f"MULTIPLE_{'LOSS' if direct_complete else 'GAIN'}_TIE_REVERSALS"
    return {"class": category, "sequence": sequence, "first_active_depth": first, "transition_depths": transitions}


def _carrier_summary(records: Sequence[Mapping[str, Any]], kind: str) -> dict[str, Any]:
    if kind == "gain":
        return {
            "items": len(records),
            "carriers": sum(len(row["gain_carriers"]) for row in records),
            "multi_carrier_items": sum(len(row["gain_carriers"]) > 1 for row in records),
            "relation": dict(sorted(Counter(
                carrier["relation"] for row in records for carrier in row["gain_carriers"]
            ).items())),
            "evidence_direct_rank": _distribution([
                carrier["direct_rank"] for row in records for carrier in row["gain_carriers"]
            ]),
            "seed_direct_rank": _distribution([
                carrier["seed_direct_rank"] for row in records for carrier in row["gain_carriers"]
            ]),
            "graph_distance": _distribution([
                carrier["graph_distance"] for row in records for carrier in row["gain_carriers"]
            ]),
            "seed_minus_evidence_score": _distribution([
                carrier["score_gap"] for row in records for carrier in row["gain_carriers"]
            ]),
            "rank_beyond_direct_selected_count": _distribution([
                carrier["rank_beyond_direct_selected_count"] for row in records for carrier in row["gain_carriers"]
            ]),
            "evidence_chars": _distribution([
                carrier["chars"] for row in records for carrier in row["gain_carriers"]
            ]),
            "linked_chars_on_gain_items": _distribution([row["linked_chars"] for row in records]),
        }
    return {
        "items": len(records),
        "carriers": sum(len(row["loss_carriers"]) for row in records),
        "multi_carrier_items": sum(len(row["loss_carriers"]) > 1 for row in records),
        "direct_selected_percentile": _distribution([
            carrier["direct_selected_percentile"] for row in records for carrier in row["loss_carriers"]
        ]),
        "direct_rank": _distribution([
            carrier["direct_rank"] for row in records for carrier in row["loss_carriers"]
        ]),
        "score": _distribution([
            carrier["direct_score"] for row in records for carrier in row["loss_carriers"]
        ]),
        "evidence_chars": _distribution([
            carrier["chars"] for row in records for carrier in row["loss_carriers"]
        ]),
        "linked_chars_on_loss_items": _distribution([row["linked_chars"] for row in records]),
        "displaced_count_on_loss_items": _distribution([row["displaced_count"] for row in records]),
        "displaced_chars_on_loss_items": _distribution([row["displaced_chars"] for row in records]),
    }


def run_analysis(
    dataset_path: Path, provenance_path: Path, preflight_path: Path,
    g6_path: Path, da001_result_path: Path, output_dir: Path,
) -> dict[str, Any]:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or sha256_file(provenance_path) != preflight["provenance_sha256"]:
        raise DA002Error("Committed DA-002 provenance anchor is absent or drifted")
    provenance = _read_gzip(provenance_path)
    provenance_by_key = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in provenance}
    records = adapt_split(dataset_path, HOLDOUT_IDS)
    evidence = {}
    for record in records:
        dialogue_to_candidate = {
            dialogue_id: source.candidate.identity
            for source in record.candidates for dialogue_id in source.dialogue_ids
        }
        for question in record.questions:
            evidence[(question.comparison_key, question.duplicate_ordinal)] = {
                dialogue_to_candidate[item] for item in question.resolved_dialogue_ids
            }
    g6_rows = json.loads(g6_path.read_text(encoding="utf-8"))["rows"]
    g6 = {(row["comparison_key"], int(row["duplicate_ordinal"])): row for row in g6_rows}
    item_rows = []
    for key, row in provenance_by_key.items():
        label = g6[key]
        if not label["primary_eligible"]:
            continue
        gold = evidence[key]
        direct_selected = set(row["arms"]["DIRECT"]["selected_ids"])
        direct_complete = gold <= direct_selected
        arms = {}
        for arm in ARMS:
            arm_row = row["arms"][arm]
            selected = set(arm_row["selected_ids"])
            complete = gold <= selected
            gain_carriers = []
            if complete and not direct_complete:
                for identity in sorted(gold - direct_selected):
                    candidate = row["candidates"][identity]
                    link = arm_row["linked_provenance"].get(identity)
                    if link is None:
                        raise DA002Error("Gain carrier lacks first-emitter link provenance")
                    gain_carriers.append({
                        "identity": identity, "direct_rank": candidate["direct_rank"],
                        "direct_score": candidate["direct_score"], "chars": candidate["chars"],
                        "direct_selected_count": candidate["direct_selected_count"],
                        "rank_beyond_direct_selected_count": candidate["direct_rank"] - candidate["direct_selected_count"],
                        **link, "score_gap": link["seed_score"] - candidate["direct_score"],
                    })
            loss_carriers = []
            if direct_complete and not complete:
                for identity in sorted(gold & direct_selected - selected):
                    candidate = row["candidates"][identity]
                    position = candidate["direct_selected_position"]
                    loss_carriers.append({
                        "identity": identity, "direct_rank": candidate["direct_rank"],
                        "direct_score": candidate["direct_score"], "chars": candidate["chars"],
                        "direct_selected_position": position,
                        "direct_selected_percentile": position / candidate["direct_selected_count"],
                    })
            arms[arm] = {
                "complete": complete, "gain": complete and not direct_complete,
                "loss": direct_complete and not complete,
                "gain_carriers": gain_carriers, "loss_carriers": loss_carriers,
                "linked_chars": arm_row["linked_chars"],
                "displaced_count": arm_row["displaced_count"],
                "displaced_chars": arm_row["displaced_chars"],
            }
        item_rows.append({
            "comparison_key": key[0], "sample_id": row["sample_id"],
            "source_index": row["source_index"], "direct_complete": direct_complete,
            "arms": arms,
        })
    if len(item_rows) != 1_098:
        raise DA002Error("DA-002 primary population differs")

    da001 = json.loads(da001_result_path.read_text(encoding="utf-8"))["matrix"]
    arm_summary = {}
    for arm in ARMS:
        gains = [row["arms"][arm] for row in item_rows if row["arms"][arm]["gain"]]
        losses = [row["arms"][arm] for row in item_rows if row["arms"][arm]["loss"]]
        complete = sum(row["arms"][arm]["complete"] for row in item_rows)
        if (complete, len(gains), len(losses)) != (
            da001[arm]["complete"], da001[arm]["gains_vs_direct"], da001[arm]["losses_vs_direct"]
        ):
            raise DA002Error(f"{arm}: DA-001 matrix reproduction differs")
        arm_summary[arm] = {
            "complete": complete, "gains": len(gains), "losses": len(losses),
            "gain_mechanism": _carrier_summary(gains, "gain"),
            "loss_mechanism": _carrier_summary(losses, "loss"),
        }

    trajectories = {}
    for family in ("TEMPORAL", "EVENT"):
        classes: Counter[str] = Counter()
        sequences: Counter[str] = Counter()
        first_depths: Counter[str] = Counter()
        transition_depths: Counter[str] = Counter()
        for row in item_rows:
            classified = classify_trajectory(
                row["direct_complete"],
                [row["arms"][f"{family}_{count}"]["complete"] for count in SEED_COUNTS],
            )
            classes[classified["class"]] += 1
            sequences[classified["sequence"]] += 1
            first_depths[str(classified["first_active_depth"])] += 1
            for depth in classified["transition_depths"]:
                transition_depths[str(depth)] += 1
        trajectories[family] = {
            "classes": dict(sorted(classes.items())), "sequences": dict(sorted(sequences.items())),
            "first_active_depths": dict(sorted(first_depths.items())),
            "transition_depths": dict(sorted(transition_depths.items())),
        }

    local_vs_deep = {}
    for count in SEED_COUNTS:
        temporal_gain = {row["comparison_key"] for row in item_rows if row["arms"][f"TEMPORAL_{count}"]["gain"]}
        event_gain = {row["comparison_key"] for row in item_rows if row["arms"][f"EVENT_{count}"]["gain"]}
        temporal_loss = {row["comparison_key"] for row in item_rows if row["arms"][f"TEMPORAL_{count}"]["loss"]}
        event_loss = {row["comparison_key"] for row in item_rows if row["arms"][f"EVENT_{count}"]["loss"]}
        event_only_keys = event_gain - temporal_gain
        event_only_distances = [
            carrier["graph_distance"]
            for row in item_rows if row["comparison_key"] in event_only_keys
            for carrier in row["arms"][f"EVENT_{count}"]["gain_carriers"]
        ]
        local_vs_deep[str(count)] = {
            "temporal_gains": len(temporal_gain), "event_gains": len(event_gain),
            "shared_gains": len(temporal_gain & event_gain),
            "event_only_gains": len(event_only_keys), "temporal_only_gains": len(temporal_gain - event_gain),
            "temporal_losses": len(temporal_loss), "event_losses": len(event_loss),
            "shared_losses": len(temporal_loss & event_loss),
            "event_only_losses": len(event_loss - temporal_loss),
            "event_only_gain_distance": _distribution(event_only_distances),
        }

    conversation = {}
    for count in SEED_COUNTS:
        arm = f"TEMPORAL_{count}"
        cells = {}
        for sample_id in sorted({row["sample_id"] for row in item_rows}):
            selected = [row for row in item_rows if row["sample_id"] == sample_id]
            gains = [row["arms"][arm] for row in selected if row["arms"][arm]["gain"]]
            losses = [row["arms"][arm] for row in selected if row["arms"][arm]["loss"]]
            cells[sample_id] = {
                "gains": len(gains), "losses": len(losses),
                "gain_mechanism": _carrier_summary(gains, "gain"),
                "loss_mechanism": _carrier_summary(losses, "loss"),
            }
        others = [row for row in item_rows if row["sample_id"] != "conv-44"]
        other_gains = [row["arms"][arm] for row in others if row["arms"][arm]["gain"]]
        other_losses = [row["arms"][arm] for row in others if row["arms"][arm]["loss"]]
        cells["OTHER_FIVE_POOLED"] = {
            "gains": len(other_gains), "losses": len(other_losses),
            "gain_mechanism": _carrier_summary(other_gains, "gain"),
            "loss_mechanism": _carrier_summary(other_losses, "loss"),
        }
        conversation[str(count)] = cells

    result = {
        "schema": "da002-mechanism-decomposition-v1",
        "standing": "post-outcome descriptive mechanism audit on spent LoCoMo",
        "population": len(item_rows), "arms": arm_summary,
        "trajectories": trajectories, "local_vs_deep": local_vs_deep,
        "temporal_by_conversation": conversation,
        "calls": {"embedding": 0, "model": 0, "cache_misses": 0},
        "claim_boundary": "mechanism explanation only; no moderator, selector, reader, or adoption",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    item_path = output_dir / "item_mechanisms.jsonl.gz"
    _write_gzip(item_path, item_rows)
    result["item_mechanisms_sha256"] = sha256_file(item_path)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["classify_trajectory", "run_analysis"]
