"""Residual blocker audit for DA-023 immutable backreference delivery."""

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
from analysis.da015_phrase_dictionary import encode
from analysis.da016_allocation import BUDGET, _payload_cost
from analysis.da023_backrefs import encoded_chars, encode_members
from analysis.nf004_anatomy_features import load_blind_cases
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "2982a79056945933267525701281ce8ae7882224ad5e9f2427e008c53fa221e4"
OUTCOME_SHA256 = "7d3a5f7a44dacc8b7b6a2a383f716b2a6b5b71dce21778f90bdbd9566013c4fd"


class DA024Error(RuntimeError):
    pass


def distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def classify(single_pair: bool, wrong_fits: bool, initial_fits: bool) -> str:
    if not single_pair:
        return "MULTI_PAIR_CONJUNCTION"
    if wrong_fits:
        return "WRONG_FROZEN_MEMBER"
    if not initial_fits:
        return "INITIAL_BACKREF_SIZE"
    return "PRIOR_ADDITIVE_CONSUMPTION"


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA024Error("LongMem population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _baseline_payloads(row: Mapping[str, Any], pair_for: Any) -> list[list[Mapping[str, str]]]:
    payloads = [list(pair_for(identity)) for identity in row["direct_ids"]]
    for action in row["baseline_actions"]:
        pair = pair_for(str(action["neighbor_id"]))
        if action["kind"] == "PAIR":
            payloads.append(list(pair))
        elif action["kind"] == "TURN":
            payloads.append([pair[int(action["member"])]])
    return payloads


def _costs(renderer: str, role: Any, history: Sequence[str], pair: Sequence[Mapping[str, str]],
           prefix: str, dictionary: Any) -> tuple[int, tuple[int, ...]]:
    if renderer == "BACKREF":
        texts = [str(member["text"]) for member in pair]
        encoded = encode_members(texts, history, prefix)
        full = append_role_pair(role, pair).chars - role.chars - sum(map(len, texts)) + encoded_chars(encoded, prefix)
        turns = []
        for member in pair:
            text = str(member["text"])
            coded = encode_members([text], history, prefix)
            turns.append(append_role_pair(role, [member]).chars - role.chars - len(text) + encoded_chars(coded, prefix))
        return full, tuple(turns)
    if dictionary is None:
        return (append_role_pair(role, pair).chars - role.chars,
                tuple(append_role_pair(role, [member]).chars - role.chars for member in pair))
    return (_payload_cost(role, pair, dictionary),
            tuple(_payload_cost(role, [member], dictionary) for member in pair))


def _states(row: Mapping[str, Any], pair_for: Any, dictionary: Any) -> tuple[Any, list[str], int, dict[str, dict[str, Any]]]:
    payloads = _baseline_payloads(row, pair_for)
    direct_count = len(row["direct_ids"])
    role = role_pattern_pairs(payloads[:direct_count])
    for payload in payloads[direct_count:]:
        role = append_role_pair(role, payload)
    history = [str(member["text"]) for payload in payloads for member in payload]
    initial_role, initial_history = role, list(history)
    used = int(row["treatment"]["baseline_chars"])
    states = {}
    for action in row["treatment"]["additions"]:
        neighbor = str(action["neighbor_id"])
        if action["kind"] == "DUPLICATE":
            pair = pair_for(neighbor)
            full, turns = _costs(row["treatment"]["renderer"], role, history, pair,
                                 row["treatment"]["prefix"], dictionary)
            states.setdefault(neighbor, {"used": used, "role": role, "history": list(history),
                                         "full": full, "turns": turns, "action": action})
            continue
        pair = pair_for(neighbor)
        full, turns = _costs(row["treatment"]["renderer"], role, history, pair,
                             row["treatment"]["prefix"], dictionary)
        if full != int(action["full_cost"]) or turns[int(action["member"] if action["member"] is not None else 0)] != int(action["turn_cost"]):
            # Pair admissions store member=None but their frozen fallback is not
            # needed for audit; only require full replay in that branch.
            if action["kind"] != "PAIR" or full != int(action["full_cost"]):
                raise DA024Error("DA-023 arrival cost replay differs")
        states[neighbor] = {"used": used, "role": role, "history": list(history),
                            "full": full, "turns": turns, "action": action}
        if action["kind"] == "PAIR":
            role = append_role_pair(role, pair)
            history.extend(str(member["text"]) for member in pair)
            used += int(action["cost"])
        elif action["kind"] == "TURN":
            member = pair[int(action["member"])]
            role = append_role_pair(role, [member])
            history.append(str(member["text"]))
            used += int(action["cost"])
    return initial_role, initial_history, int(row["treatment"]["baseline_chars"]), states


def _audit_item(corpus: str, key: str, group: str, row: Mapping[str, Any], missing: set[str],
                pair_for: Any, identities: Mapping[str, Sequence[str]], dictionary: Any) -> dict[str, Any]:
    initial_role, initial_history, initial_used, states = _states(row, pair_for, dictionary)
    carriers = []
    for action in row["baseline_actions"]:
        neighbor = str(action["neighbor_id"])
        carried = set(identities[neighbor])
        if carried & missing:
            carriers.append(neighbor)
    carriers = list(dict.fromkeys(carriers))
    if not carriers or not missing <= set().union(*(set(identities[value]) for value in carriers)):
        raise DA024Error("Residual carrier join differs")
    single = [value for value in carriers if missing <= set(identities[value])]
    if not single:
        return {"corpus": corpus, "key": key, "group": group, "blocker": "MULTI_PAIR_CONJUNCTION",
                "missing": sorted(missing), "carrier_count": len(carriers), "carriers": carriers}
    carrier = single[0]
    pair = pair_for(carrier)
    if carrier in states:
        state = states[carrier]
    else:
        full, turns = _costs(row["treatment"]["renderer"], initial_role, initial_history, pair,
                             row["treatment"]["prefix"], dictionary)
        baseline_position, baseline_action = next(
            ((index, action) for index, action in enumerate(row["baseline_actions"])
             if str(action["neighbor_id"]) == carrier and action["kind"] in {"PAIR", "TURN"}),
            (None, None),
        )
        if baseline_action is None:
            raise DA024Error("Carrier has no baseline or additive state")
        state = {"used": initial_used, "role": initial_role, "history": initial_history,
                 "full": full, "turns": turns,
                 "action": {**baseline_action, "position": baseline_position}}
    required_members = [index for index, target in enumerate(identities[carrier]) if target in missing]
    materialization = "TURN" if len(required_members) == 1 else "PAIR"
    required_index = required_members[0] if materialization == "TURN" else None
    arrival_cost = state["turns"][required_index] if materialization == "TURN" else state["full"]
    initial_full, initial_turns = _costs(row["treatment"]["renderer"], initial_role, initial_history, pair,
                                         row["treatment"]["prefix"], dictionary)
    initial_cost = initial_turns[required_index] if materialization == "TURN" else initial_full
    frozen = state["action"].get("member")
    if frozen is None:
        baseline_turn = next((action for action in row["baseline_actions"]
                              if str(action["neighbor_id"]) == carrier and action["kind"] == "TURN"), None)
        frozen = None if baseline_turn is None else baseline_turn.get("member")
    frozen_omits = materialization == "TURN" and frozen is not None and int(frozen) != required_index
    wrong_fits = frozen_omits and state["used"] + arrival_cost <= BUDGET
    blocker = classify(True, wrong_fits, initial_used + initial_cost <= BUDGET)
    return {"corpus": corpus, "key": key, "group": group, "blocker": blocker,
            "missing": sorted(missing), "carrier_count": len(carriers), "carrier": carrier,
            "materialization": materialization, "required_member": required_index,
            "frozen_member": frozen, "initial_used": initial_used, "arrival_used": state["used"],
            "initial_slack": BUDGET - initial_used, "arrival_slack": BUDGET - state["used"],
            "initial_cost": initial_cost, "arrival_cost": arrival_cost,
            "position": int(state["action"]["position"])}


def audit(locomo_path: Path, longmem_path: Path, population_path: Path,
          selection_path: Path, outcome_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(outcome_path) != OUTCOME_SHA256:
        raise DA024Error("DA-024 sealed parent differs")
    selections = list(read_gzip(selection_path))
    outcomes = {f"{row['corpus']}:{row['key']}": row for row in read_gzip(outcome_path)}
    nf_cases = load_blind_cases(locomo_path)
    nf_members, _ = _member_maps(locomo_path, nf_cases)
    nf_pairs, nf_groups = {}, {}
    for record in adapt_split(locomo_path, HOLDOUT_IDS):
        for source in record.candidates:
            nf_pairs[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            nf_groups[f"{question.comparison_key}:{question.duplicate_ordinal}"] = question.sample_id
    long_records = {record.question_id: record for record in adapt_population(longmem_path, _population_ids(population_path))}
    long_blind = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    classifications = []
    for row in selections:
        if row["corpus"] == "NF004":
            key = f"{row['comparison_key']}:{row['duplicate_ordinal']}"
            outcome = outcomes[f"NF004:{key}"]
            if outcome["TREATMENT"] or not outcome["missing_control"]:
                continue
            missing = set(outcome["missing_control"]) - set(outcome["carried_missing"])
            # Only ceiling-reachable residuals have complete exposed union.
            exposed = set().union(*(set(nf_pairs[str(a["neighbor_id"])]) for a in row["baseline_actions"]))
            if not missing <= exposed:
                continue
            classifications.append(_audit_item("NF004", key, nf_groups[key], row, missing,
                                               lambda identity: nf_members[identity], nf_pairs, None))
        else:
            key = str(row["question_id"])
            outcome = outcomes[f"LONGMEM:{key}"]
            if outcome["TREATMENT"] or not outcome["missing_control"]:
                continue
            record = long_records[key]
            by_id = {episode.candidate.identity: episode for episode in long_blind[key].episodes}
            identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
            missing = set(outcome["missing_control"]) - set(outcome["carried_missing"])
            exposed = set().union(*(set(identities[str(a["neighbor_id"])]) for a in row["baseline_actions"]))
            if not missing <= exposed:
                continue
            direct_texts = [str(member["text"]) for identity in row["direct_ids"] for member in by_id[identity].members]
            classifications.append(_audit_item("LONGMEM", key, record.question_type, row, missing,
                                               lambda identity: by_id[identity].members, identities, encode(direct_texts)))
    counts = {corpus: Counter(row["blocker"] for row in classifications if row["corpus"] == corpus)
              for corpus in ("NF004", "LONGMEM")}
    if sum(counts["NF004"].values()) != 10 or sum(counts["LONGMEM"].values()) != 48:
        raise DA024Error(f"DA-024 residual populations differ: {counts}")
    corpora = {}
    for corpus in counts:
        subset = [row for row in classifications if row["corpus"] == corpus]
        top, number = counts[corpus].most_common(1)[0]
        status = f"DOMINANT_{top}" if number / len(subset) >= .6 else "MIXED_RESIDUAL_BLOCKERS"
        finite = [row for row in subset if "initial_cost" in row]
        corpora[corpus] = {"n": len(subset), "blockers": dict(counts[corpus]), "status": status,
                           "initial_slack": distribution([row["initial_slack"] for row in finite]),
                           "arrival_slack": distribution([row["arrival_slack"] for row in finite]),
                           "initial_cost": distribution([row["initial_cost"] for row in finite]),
                           "arrival_cost": distribution([row["arrival_cost"] for row in finite])}
    shared = corpora["NF004"]["status"] if corpora["NF004"]["status"] == corpora["LONGMEM"]["status"] and corpora["NF004"]["status"].startswith("DOMINANT") else None
    result = {"schema": "da024-residual-audit-v1", "corpora": corpora,
              "shared_successor_signal": shared,
              "anchors": {"NF004": {"direct": 935, "control": 970, "treatment": 976, "ceiling": 986},
                          "LONGMEM": {"direct": 164, "control": 188, "treatment": 202, "ceiling": 250}},
              "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent evidence-aware causal audit only"}
    return result, classifications


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_audit(locomo_path: Path, longmem_path: Path, population_path: Path,
              selection_path: Path, outcome_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = audit(locomo_path, longmem_path, population_path, selection_path, outcome_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "classifications.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da024-") as directory:
        replay_result, replay_rows = audit(locomo_path, longmem_path, population_path, selection_path, outcome_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "classifications_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA024Error("DA-024 replay differs")
    return result


__all__ = ["DA024Error", "audit", "classify", "run_audit"]
