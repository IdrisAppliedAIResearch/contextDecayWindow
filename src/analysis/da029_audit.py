"""Residual dependency audit after DA-028 compact allocation."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import POPULATION_SHA256, load_blind_population, sha256_file
from analysis.da027_allocation import _costs, _descriptors
from analysis.da027_compact_backrefs import encode_members, encoded_chars, prefix_for
from analysis.nf004_anatomy_features import load_blind_cases
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split
from analysis.nf005_measurement import adapt_population

BUDGET = 16_000
SELECTION_SHA256 = "0ae01f5cdbc4d244c3188778f1b90292211101a56d118e467bd8c9f32b44f21a"
OUTCOME_SHA256 = "18b77b06e3c9b27b192ba4e0fd9c4c9d89f36111f625914145e8ca8019a41a46"
CLASSIFICATION_SHA256 = "22225c9563bf82b12a9a9804d75e227722242148f9f7454420afc0619046d771"


class DA029Error(RuntimeError):
    pass


def distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA029Error("LongMem population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _compact_states(row: Mapping[str, Any], pair_for: Any) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    descriptors = _descriptors({**row, "treatment": row["da023"]}, pair_for)
    payloads = [[pair_for(identity)[index] for index in members] for identity, members in descriptors]
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    prefix = prefix_for([str(member["text"]) for identity in dict.fromkeys(
        list(map(str, row["direct_ids"])) + [str(a["neighbor_id"]) for a in row["baseline_actions"]])
                         for member in pair_for(identity)])
    encoded = encode_members(history, (), prefix)
    compact = role.chars - sum(map(len, history)) + encoded_chars(encoded, prefix)
    if compact != int(row["treatment"]["selected_chars"]):
        raise DA029Error("Initial compact state differs")
    initial = {"used": compact, "role": role, "history": list(history)}
    states = {}
    used = compact
    for action in row["treatment"]["actions"]:
        neighbor = str(action["neighbor_id"])
        pair = pair_for(neighbor)
        full, turns, _, _ = _costs(role, history, pair, prefix)
        states[neighbor] = {"used": used, "role": role, "history": list(history),
                            "full": full, "turns": turns, "action": action}
        member = action.get("member")
        if int(action["full_cost"]) != full or int(action["turn_cost"]) != turns[int(member if member is not None else 0)]:
            if action["kind"] != "PAIR" or int(action["full_cost"]) != full:
                raise DA029Error("Compact arrival cost differs")
        if action["kind"] == "PAIR":
            role = append_role_pair(role, pair)
            history.extend(str(item["text"]) for item in pair)
            used += int(action["cost"])
        elif action["kind"] == "TURN":
            selected = int(action["member"])
            role = append_role_pair(role, [pair[selected]])
            history.append(str(pair[selected]["text"]))
            used += int(action["cost"])
    if used != int(row["treatment"]["final_chars"]):
        raise DA029Error("Final compact state differs")
    return initial, states


def _frozen_member(row: Mapping[str, Any], carrier: str) -> int | None:
    for action in row["da023"]["additions"]:
        if str(action["neighbor_id"]) == carrier and action.get("member") is not None:
            return int(action["member"])
    for action in row["baseline_actions"]:
        if str(action["neighbor_id"]) == carrier and action.get("member") is not None:
            return int(action["member"])
    return None


def _classify(corpus: str, key: str, row: Mapping[str, Any], missing: set[str], pair_for: Any,
              identities: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    carriers = list(dict.fromkeys(str(action["neighbor_id"]) for action in row["baseline_actions"]
                                 if set(identities[str(action["neighbor_id"])]) & missing))
    if not carriers or not missing <= set().union(*(set(identities[value]) for value in carriers)):
        raise DA029Error("Residual exposed union differs")
    single = [value for value in carriers if missing <= set(identities[value])]
    if not single:
        return {"corpus": corpus, "key": key, "blocker": "MULTI_CARRIER_CONJUNCTION",
                "missing": sorted(missing), "carrier_count": len(carriers),
                "required_member_count": sum(bool(set(identities[value]) & missing) for value in carriers)}
    carrier = single[0]
    if row["treatment"]["codec"] == "DA023":
        return {"corpus": corpus, "key": key, "blocker": "RETAINED_CODEC_NO_TAIL",
                "missing": sorted(missing), "carrier": carrier}
    initial, states = _compact_states(row, pair_for)
    pair = pair_for(carrier)
    required = [index for index, identity in enumerate(identities[carrier]) if identity in missing]
    materialization = "TURN" if len(required) == 1 else "PAIR"
    required_member = required[0] if materialization == "TURN" else None
    initial_full, initial_turns, _, _ = _costs(initial["role"], initial["history"], pair,
                                                row["treatment"]["prefix"])
    state = states.get(carrier)
    if state is None:
        state = {**initial, "full": initial_full, "turns": initial_turns, "action": None}
    initial_cost = initial_turns[required_member] if materialization == "TURN" else initial_full
    arrival_cost = state["turns"][required_member] if materialization == "TURN" else state["full"]
    frozen = _frozen_member(row, carrier)
    wrong_fits = (materialization == "TURN" and frozen is not None and frozen != required_member
                  and state["used"] + arrival_cost <= BUDGET)
    if wrong_fits:
        blocker = "WRONG_FROZEN_MEMBER"
    elif initial["used"] + initial_cost > BUDGET:
        blocker = "INITIAL_COMPACT_SIZE"
    elif state["used"] + arrival_cost > BUDGET:
        blocker = "PRIOR_COMPACT_CONSUMPTION"
    else:
        blocker = "UNACCOUNTED"
    return {"corpus": corpus, "key": key, "blocker": blocker, "missing": sorted(missing),
            "carrier": carrier, "materialization": materialization,
            "required_member": required_member, "frozen_member": frozen,
            "initial_used": initial["used"], "arrival_used": state["used"],
            "initial_slack": BUDGET - initial["used"], "arrival_slack": BUDGET - state["used"],
            "initial_cost": initial_cost, "arrival_cost": arrival_cost,
            "position": None if state["action"] is None else int(state["action"]["position"])}


def audit(locomo_path: Path, longmem_path: Path, population_path: Path, selection_path: Path,
          outcome_path: Path, classification_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((selection_path, SELECTION_SHA256), (outcome_path, OUTCOME_SHA256),
             (classification_path, CLASSIFICATION_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA029Error("Sealed input differs")
    selections = list(read_gzip(selection_path))
    outcomes = {f"{row['corpus']}:{row['key']}": row for row in read_gzip(outcome_path)}
    prior = list(read_gzip(classification_path))
    nf_rows = {f"{row['comparison_key']}:{row['duplicate_ordinal']}": row
               for row in selections if row["corpus"] == "NF004"}
    long_rows = {str(row["question_id"]): row for row in selections if row["corpus"] == "LONGMEM"}
    nf_members, _ = _member_maps(locomo_path, load_blind_cases(locomo_path))
    nf_identities = {}
    for record in adapt_split(locomo_path, HOLDOUT_IDS):
        for source in record.candidates:
            nf_identities[source.candidate.identity] = tuple(source.dialogue_ids)
    long_blind = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    long_records = {record.question_id: record
                    for record in adapt_population(longmem_path, _population_ids(population_path))}
    output = []
    for item in prior:
        corpus, key = str(item["corpus"]), str(item["key"])
        if outcomes[f"{corpus}:{key}"]["TREATMENT"]:
            continue
        missing = set(item["missing"])
        if corpus == "NF004":
            row = nf_rows[key]
            output.append(_classify(corpus, key, row, missing,
                                    lambda identity: nf_members[identity], nf_identities))
        else:
            row, blind, record = long_rows[key], long_blind[key], long_records[key]
            by_id = {episode.candidate.identity: episode for episode in blind.episodes}
            identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
            output.append(_classify(corpus, key, row, missing,
                                    lambda identity: by_id[identity].members, identities))
    counts = {corpus: Counter(row["blocker"] for row in output if row["corpus"] == corpus)
              for corpus in ("NF004", "LONGMEM")}
    if sum(counts["NF004"].values()) != 9 or sum(counts["LONGMEM"].values()) != 42:
        raise DA029Error(f"Residual cardinality differs: {counts}")
    if any(counter["UNACCOUNTED"] for counter in counts.values()):
        raise DA029Error(f"Unaccounted residual: {counts}")
    corpora = {}
    for corpus, counter in counts.items():
        subset = [row for row in output if row["corpus"] == corpus]
        top, number = counter.most_common(1)[0]
        status = f"DOMINANT_{top}" if number / len(subset) >= .6 else "MIXED_RESIDUAL_BLOCKERS"
        finite = [row for row in subset if "initial_cost" in row]
        corpora[corpus] = {"n": len(subset), "blockers": dict(counter), "status": status,
                           "initial_slack": distribution([row["initial_slack"] for row in finite]),
                           "arrival_slack": distribution([row["arrival_slack"] for row in finite]),
                           "initial_cost": distribution([row["initial_cost"] for row in finite]),
                           "arrival_cost": distribution([row["arrival_cost"] for row in finite])}
    shared = (corpora["NF004"]["status"] if corpora["NF004"]["status"] == corpora["LONGMEM"]["status"]
              and corpora["NF004"]["status"].startswith("DOMINANT") else None)
    result = {"schema": "da029-compact-residual-audit-v1", "corpora": corpora,
              "shared_successor_signal": shared,
              "anchors": {"NF004": {"treatment": 977, "ceiling": 986},
                          "LONGMEM": {"treatment": 208, "ceiling": 250}},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent evidence-aware causal audit only"}
    return result, output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_audit(locomo_path: Path, longmem_path: Path, population_path: Path, selection_path: Path,
              outcome_path: Path, classification_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(locomo_path, longmem_path, population_path, selection_path,
                         outcome_path, classification_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "classifications.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da029-") as directory:
        replay_result, replay_rows = audit(locomo_path, longmem_path, population_path, selection_path,
                                           outcome_path, classification_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "classifications_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA029Error("Audit replay differs")
    return result


__all__ = ["DA029Error", "audit", "distribution", "run_audit"]
