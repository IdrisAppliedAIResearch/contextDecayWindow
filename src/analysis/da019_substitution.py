"""Blind one-swap boundary substitution for DA-019."""

from __future__ import annotations

import gzip
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from analysis.da003_edge_features import tokens
from analysis.da004_pack_features import read_gzip
from analysis.da006_reserved_links import _member_maps
from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da013_preflight import _tokens, load_blind_population, sha256_file
from analysis.da015_phrase_dictionary import encode
from analysis.da016_allocation import BUDGET, _payload_cost
from analysis.nf004_anatomy_features import load_blind_cases

NF_ROLE_SHA256 = "0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb"
NF_EDGE_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
NF_PAYLOAD_SHA256 = "51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3"
NF_ORDER_SHA256 = "877058e2d2499bb62f3d40ac28dbe4f6f1bc168467d42b16e37b3ace934c1146"
NF_CONTROL_SHA256 = "d69a5e1a1585f0e1988bb6599af9fd53d2d84c5d4d70e3783d96c6427839d9b8"
LONG_CONTROL_SHA256 = "8ab71c95ee4cea7c78149e344ea704243cfbfa2acbfc9eddd70b105e32d39a64"
LONG_DIRECT_SHA256 = "9544fd5bc6ad85515f5cb99472cb844e2c8b9f97cd1f51a19de2d882da47ff5c"
DA018_SHA256 = "3928700040ffe7931b5865414867b149595db67a431f32dc97a72d4e9f7ffcdb"


class DA019Error(RuntimeError):
    pass


def _qkey(row: Mapping[str, Any]) -> tuple[str, int]:
    return str(row["comparison_key"]), int(row["duplicate_ordinal"])


def _ekey(row: Mapping[str, Any]) -> tuple[str, int, str, str]:
    return (*_qkey(row), str(row["seed_id"]), str(row["neighbor_id"]))


def unique_query_tokens(query: frozenset[str], incumbent: frozenset[str],
                        retained: frozenset[str]) -> frozenset[str]:
    return (query & incumbent) - retained


def guard(fits: bool, required: frozenset[str], candidate: frozenset[str],
          incumbent_cosine: float, candidate_cosine: float) -> tuple[bool, tuple[str, ...]]:
    reasons = []
    if not fits:
        reasons.append("FIT")
    if not required <= candidate:
        reasons.append("LEXICAL")
    if candidate_cosine < incumbent_cosine:
        reasons.append("SEMANTIC")
    return not reasons, tuple(reasons)


def duplicate_rejection(neighbor: str, retained: set[str], incumbent: str) -> tuple[str, ...]:
    return ("DUPLICATE",) if neighbor in retained or neighbor == incumbent else ()


def _payload(pair: Sequence[Mapping[str, str]], kind: str, member: int | None) -> list[Mapping[str, str]]:
    return list(pair) if kind == "PAIR" else [pair[int(member)]]


def _substitute(
    query: frozenset[str], direct_ids: Sequence[str], baseline: Sequence[Mapping[str, Any]],
    pair_for: Callable[[str], Sequence[Mapping[str, str]]], initial_role: Any, initial_chars: int,
    cost_for: Callable[[Any, Sequence[Mapping[str, str]]], int],
) -> dict[str, Any]:
    admitted = [index for index, action in enumerate(baseline) if action["kind"] in {"PAIR", "TURN"}]
    if not admitted:
        return {"executed": False, "reason": "NO_INCUMBENT", "final_chars": initial_chars,
                "actions": list(baseline), "evaluations": []}
    incumbent_index = admitted[-1]
    incumbent = baseline[incumbent_index]
    role, used = initial_role, initial_chars
    retained_tokens = set().union(*(tokens(str(member["text"])) for identity in direct_ids for member in pair_for(identity)))
    retained_neighbors = set(map(str, direct_ids))
    rebuilt = []
    for index, action in enumerate(baseline):
        if index == incumbent_index or action["kind"] not in {"PAIR", "TURN"}:
            continue
        pair = pair_for(str(action["neighbor_id"]))
        payload = _payload(pair, str(action["kind"]), action.get("member"))
        cost = cost_for(role, payload)
        role = append_role_pair(role, payload)
        used += cost
        retained_tokens.update(*(tokens(str(member["text"])) for member in payload))
        retained_neighbors.add(str(action["neighbor_id"]))
        rebuilt.append({**action, "cost": cost})
    incumbent_pair = pair_for(str(incumbent["neighbor_id"]))
    incumbent_payload = _payload(incumbent_pair, str(incumbent["kind"]), incumbent.get("member"))
    incumbent_tokens = frozenset().union(*(tokens(str(member["text"])) for member in incumbent_payload))
    required = unique_query_tokens(query, incumbent_tokens, frozenset(retained_tokens))
    evaluations = []
    selected = None
    for position, action in enumerate(baseline):
        if action["kind"] != "SKIP":
            continue
        neighbor = str(action["neighbor_id"])
        duplicate = duplicate_rejection(neighbor, retained_neighbors, str(incumbent["neighbor_id"]))
        if duplicate:
            evaluations.append({"position": position, "neighbor_id": neighbor, "reasons": list(duplicate)})
            continue
        pair = pair_for(neighbor)
        full_cost = cost_for(role, pair)
        member = int(action["member"])
        turn_cost = cost_for(role, [pair[member]])
        if used + full_cost <= BUDGET:
            kind, payload, cost = "PAIR", list(pair), full_cost
        else:
            kind, payload, cost = "TURN", [pair[member]], turn_cost
        candidate_tokens = frozenset().union(*(tokens(str(item["text"])) for item in payload))
        accepted, reasons = guard(used + cost <= BUDGET, required, candidate_tokens,
                                  float(incumbent["payload_cosine"]), float(action["payload_cosine"]))
        evaluation = {"position": position, "seed_id": action.get("seed_id"), "neighbor_id": neighbor,
                      "kind": kind, "member": member if kind == "TURN" else None, "cost": cost,
                      "full_cost": full_cost, "turn_cost": turn_cost,
                      "payload_cosine": float(action["payload_cosine"]), "required_tokens": sorted(required),
                      "candidate_query_tokens": sorted(query & candidate_tokens), "reasons": list(reasons)}
        evaluations.append(evaluation)
        if accepted:
            selected = {**evaluation, "reasons": [], "kind": kind,
                        "member": member if kind == "TURN" else None}
            role = append_role_pair(role, payload)
            used += cost
            break
    if selected is None:
        return {"executed": False, "reason": "NO_QUALIFYING_SKIP", "final_chars": int(baseline[-1]["final_chars"]),
                "actions": list(baseline), "incumbent": dict(incumbent), "evaluations": evaluations}
    final_actions = [dict(action) for index, action in enumerate(baseline) if index != incumbent_index]
    final_actions.append({"seed_id": selected.get("seed_id"), "neighbor_id": selected["neighbor_id"],
                          "kind": selected["kind"], "member": selected["member"], "cost": selected["cost"],
                          "payload_cosine": selected["payload_cosine"], "substitution": True})
    return {"executed": True, "reason": "SUBSTITUTED", "final_chars": used,
            "incumbent": dict(incumbent), "replacement": selected,
            "actions": final_actions, "evaluations": evaluations}


def _nf_baseline(role: Any, direct_ids: Sequence[str], order_actions: Sequence[Mapping[str, Any]],
                 edge_map: Mapping[tuple[str, int, str, str], Mapping[str, Any]],
                 members: Mapping[str, Sequence[Mapping[str, str]]],
                 payloads: Mapping[tuple[str, int, str, str], Mapping[str, Any]], key: tuple[str, int]) -> list[dict[str, Any]]:
    used = role.chars
    seen = set(map(str, direct_ids))
    actions = []
    for ordered in order_actions:
        if "seed_id" not in ordered:
            continue
        edge_key = (*key, str(ordered["seed_id"]), str(ordered["neighbor_id"]))
        edge = edge_map[edge_key]
        neighbor = str(edge["neighbor_id"])
        if neighbor in seen:
            continue
        seen.add(neighbor)
        pair = members[neighbor]
        full = append_role_pair(role, pair)
        selected = int(payloads[edge_key]["selected_member_index"])
        turn = append_role_pair(role, [pair[selected]])
        if full.chars <= BUDGET:
            kind, member, cost, role = "PAIR", None, full.chars - role.chars, full
        elif turn.chars <= BUDGET:
            kind, member, cost, role = "TURN", selected, turn.chars - role.chars, turn
        else:
            kind, member, cost = "SKIP", selected, 0
        used += cost
        actions.append({"seed_id": str(edge["seed_id"]), "neighbor_id": neighbor, "kind": kind,
                        "member": member, "cost": cost,
                        "payload_cosine": float(edge["features"]["neighbor_query_cosine"]), "final_chars": used})
    return actions


def build_nf_rows(dataset_path: Path, role_path: Path, edge_path: Path, payload_path: Path,
                  order_path: Path, control_path: Path) -> list[dict[str, Any]]:
    seals = ((role_path, NF_ROLE_SHA256), (edge_path, NF_EDGE_SHA256), (payload_path, NF_PAYLOAD_SHA256),
             (order_path, NF_ORDER_SHA256), (control_path, NF_CONTROL_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA019Error("DA-019 NF input differs")
    cases = load_blind_cases(dataset_path)
    members, questions = _member_maps(dataset_path, cases)
    roles = {_qkey(row): row for row in read_gzip(role_path)}
    payloads = {_ekey(row): row for row in read_gzip(payload_path)}
    edges = {_ekey(row): row for row in read_gzip(edge_path)}
    orders = {_qkey(row): row for row in read_gzip(order_path)}
    controls = {_qkey(row): row for row in read_gzip(control_path)}
    output = []
    for key in sorted(orders):
        sealed = roles[key]
        direct_ids = list(sealed["direct_ids"])
        role = role_pattern_pairs([members[value] for value in direct_ids])
        baseline = _nf_baseline(role, direct_ids, orders[key]["actions"], edges, members, payloads, key)
        control = controls[key]["arms"]["PAIR_THEN_TURN"]
        linked = []
        for action in baseline:
            if action["kind"] == "PAIR":
                linked.extend(str(member["dialogue_id"]) for member in members[action["neighbor_id"]])
            elif action["kind"] == "TURN":
                linked.append(str(members[action["neighbor_id"]][int(action["member"])]["dialogue_id"]))
        if linked != control["linked_dialogue_ids"] or baseline[-1]["final_chars"] != control["total_chars"]:
            raise DA019Error("DA-019 NF control replay differs")
        treatment = _substitute(tokens(questions[key]), direct_ids, baseline,
                                lambda identity: members[identity], role, role.chars,
                                lambda state, pair: append_role_pair(state, pair).chars - state.chars)
        output.append({"corpus": "NF004", "comparison_key": key[0], "duplicate_ordinal": key[1],
                       "sample_id": sealed["sample_id"], "source_index": sealed["source_index"],
                       "direct_ids": direct_ids, "baseline_actions": baseline, "treatment": treatment})
    if len(output) != 1_098:
        raise DA019Error("DA-019 NF population differs")
    return output


def build_long_rows(longmem_path: Path, population_path: Path, control_path: Path,
                    direct_path: Path, da018_path: Path) -> list[dict[str, Any]]:
    if (sha256_file(control_path) != LONG_CONTROL_SHA256 or
            sha256_file(direct_path) != LONG_DIRECT_SHA256 or
            sha256_file(da018_path) != DA018_SHA256):
        raise DA019Error("DA-019 LongMem input differs")
    records = {record.question_id: record for record in load_blind_population(longmem_path, population_path)}
    controls = {str(row["question_id"]): row for row in read_gzip(control_path)}
    directs = {str(row["question_id"]): row for row in read_gzip(direct_path)}
    da018 = {str(row["question_id"]): row for row in read_gzip(da018_path) if row["corpus"] == "LONGMEM"}
    output = []
    for question_id in sorted(records):
        record, control = records[question_id], controls[question_id]
        fallback_by_neighbor = {str(edge["neighbor_id"]): int(edge["fallback_member"])
                                for edge in directs[question_id]["edges"]}
        by_id = {episode.candidate.identity: episode for episode in record.episodes}
        direct_ids = list(control["direct_ids"])
        direct_pairs = [by_id[value].members for value in direct_ids]
        role = role_pattern_pairs(direct_pairs)
        texts = [str(member["text"]) for pair in direct_pairs for member in pair]
        dictionary = encode(texts)
        phrase_chars = role.chars - sum(map(len, texts)) + dictionary.content_chars + dictionary.declaration_chars
        cosine = {}
        fallback_members = {}
        for action in da018[question_id]["arms"]["PAYLOAD_COSINE"]["actions"]:
            if "payload_cosine" in action:
                cosine[str(action["neighbor_id"])] = float(action["payload_cosine"])
                if action.get("member") is not None:
                    fallback_members[str(action["neighbor_id"])] = int(action["member"])
        baseline = []
        for action in control["actions"]:
            row = dict(action)
            row["payload_cosine"] = cosine[str(action["neighbor_id"])]
            if row["kind"] == "SKIP" and row.get("member") is None:
                row["member"] = fallback_members.get(
                    str(action["neighbor_id"]), fallback_by_neighbor[str(action["neighbor_id"])]
                )
            row["final_chars"] = 0
            baseline.append(row)
        running = phrase_chars
        for action in baseline:
            running += int(action["cost"])
            action["final_chars"] = running
        if running != int(control["final_chars"]):
            raise DA019Error("DA-019 LongMem control replay differs")
        treatment = _substitute(_tokens(record.question), direct_ids, baseline,
                                lambda identity: by_id[identity].members, role, phrase_chars,
                                lambda state, pair: _payload_cost(state, pair, dictionary))
        output.append({"corpus": "LONGMEM", "question_id": question_id,
                       "question_type": record.question_type, "direct_ids": direct_ids,
                       "baseline_actions": baseline, "treatment": treatment})
    if len(output) != 465:
        raise DA019Error("DA-019 LongMem population differs")
    return output


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_preflight(nf_args: Mapping[str, Path], long_args: Mapping[str, Path], output_dir: Path) -> dict[str, Any]:
    rows = [*build_nf_rows(**nf_args), *build_long_rows(**long_args)]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "blind_substitutions.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da019-") as directory:
        replay_rows = [*build_nf_rows(**nf_args), *build_long_rows(**long_args)]
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = path.read_bytes() == replay.read_bytes()
    activity = {}
    rejection = Counter()
    for corpus in ("NF004", "LONGMEM"):
        subset = [row for row in rows if row["corpus"] == corpus]
        activity[corpus] = {"questions": len(subset),
                            "executed": sum(row["treatment"]["executed"] for row in subset),
                            "unchanged": sum(not row["treatment"]["executed"] for row in subset)}
        for row in subset:
            for evaluation in row["treatment"]["evaluations"]:
                rejection.update(evaluation["reasons"])
    active = all(activity[corpus]["executed"] for corpus in activity)
    missing_rejections = [name for name in ("FIT", "LEXICAL", "SEMANTIC", "DUPLICATE") if not rejection[name]]
    passed = identical and active and not missing_rejections
    status = "PASS" if passed else "BOUNDARY_GUARD_INERT" if not active else "STOPPED_AT_PF4"
    result = {"schema": "da019-blind-substitution-v1", "status": status,
              "activity": activity, "rejections": dict(sorted(rejection.items())),
              "missing_required_rejections": missing_rejections,
              "selection_sha256": sha256_file(path), "replay_byte_identical": identical,
              "calls": {"embedding": 0, "model": 0, "cache_access": 0}}
    (output_dir / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


__all__ = ["DA019Error", "build_long_rows", "build_nf_rows", "duplicate_rejection", "guard",
           "run_preflight", "unique_query_tokens"]
