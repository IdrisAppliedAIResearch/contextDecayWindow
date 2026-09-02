"""Exact cross-corpus evidence analysis for DA-023 backreference allocations."""

from __future__ import annotations

import gzip
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from analysis.da004_pack_features import read_gzip
from analysis.da013_preflight import POPULATION_SHA256, sha256_file
from analysis.nf004_measurement import HOLDOUT_IDS, adapt_split
from analysis.nf005_measurement import adapt_population

SELECTION_SHA256 = "2982a79056945933267525701281ce8ae7882224ad5e9f2427e008c53fa221e4"
NF_EDGE_SHA256 = "e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4"
LONG_EDGE_SHA256 = "9544fd5bc6ad85515f5cb99472cb844e2c8b9f97cd1f51a19de2d882da47ff5c"


class DA023AnalysisError(RuntimeError):
    pass


def paired(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gains = sum(not row["CONTROL"] and row["TREATMENT"] for row in rows)
    losses = sum(row["CONTROL"] and not row["TREATMENT"] for row in rows)
    n = gains + losses
    tail = min(gains, losses)
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(tail + 1)) / 2**n) if n else 1.0
    return {"gains": gains, "losses": losses, "net": gains - losses,
            "ties": len(rows) - n, "discordant": n, "two_sided_exact_p": p}


def distribution(values: Sequence[int | float]) -> dict[str, float] | None:
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return {name: float(np.percentile(array, q)) for name, q in (("p10", 10), ("p50", 50), ("p90", 90))}


def _population_ids(path: Path) -> frozenset[str]:
    if sha256_file(path) != POPULATION_SHA256:
        raise DA023AnalysisError("DA-023 LongMem population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]]) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(identities[str(action["neighbor_id"])])
        elif action["kind"] == "TURN":
            output.add(identities[str(action["neighbor_id"])][int(action["member"])])
    return output


def _action_rows(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]],
                 missing: set[str], rank_for: Any) -> list[dict[str, Any]]:
    output = []
    for action in actions:
        if action["kind"] not in {"PAIR", "TURN"}:
            continue
        carried = set(identities[str(action["neighbor_id"])]) if action["kind"] == "PAIR" else {
            identities[str(action["neighbor_id"])][int(action["member"])]}
        output.append({"kind": action["kind"], "cost": int(action["cost"]),
                       "position": int(action["position"]), "seed_rank": int(rank_for(action)),
                       "neighbor_id": str(action["neighbor_id"]),
                       "carries_missing": bool(carried & missing)})
    return output


def analyze(locomo_path: Path, longmem_path: Path, population_path: Path,
            selection_path: Path, nf_edge_path: Path,
            long_edge_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    seals = ((selection_path, SELECTION_SHA256), (nf_edge_path, NF_EDGE_SHA256),
             (long_edge_path, LONG_EDGE_SHA256))
    if any(sha256_file(path) != digest for path, digest in seals):
        raise DA023AnalysisError("DA-023 sealed input differs")
    selections = list(read_gzip(selection_path))
    nf_selections = {(str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
                     for row in selections if row["corpus"] == "NF004"}
    long_selections = {str(row["question_id"]): row for row in selections if row["corpus"] == "LONGMEM"}
    nf_edges = {(str(row["comparison_key"]), int(row["duplicate_ordinal"]), str(row["seed_id"]), str(row["neighbor_id"])): row
                for row in read_gzip(nf_edge_path)}
    long_edges = {str(row["question_id"]): {str(edge["neighbor_id"]): edge for edge in row["edges"]}
                  for row in read_gzip(long_edge_path)}

    nf_evidence, nf_pairs, nf_meta = {}, {}, {}
    for record in adapt_split(locomo_path, HOLDOUT_IDS):
        for source in record.candidates:
            nf_pairs[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            nf_evidence[key] = set(question.resolved_dialogue_ids)
            nf_meta[key] = (question.sample_id, question.source_index)
    rows, mechanisms = [], {"NF004": [], "LONGMEM": []}
    for key in sorted(nf_selections):
        selection = nf_selections[key]
        direct = set().union(*(nf_pairs[value] for value in selection["direct_ids"]))
        control_links = _delivered(selection["baseline_actions"], nf_pairs)
        added = selection["treatment"]["additions"]
        added_links = _delivered(added, nf_pairs)
        gold = nf_evidence[key]
        missing = gold - (direct | control_links)
        control, treatment = gold <= direct | control_links, gold <= direct | control_links | added_links
        if control and not treatment:
            raise DA023AnalysisError("DA-023 NF control loss")
        if treatment and not control and not missing <= added_links:
            raise DA023AnalysisError("DA-023 NF gain lacks carrier")
        action_rows = _action_rows(
            added, nf_pairs, missing,
            lambda action: nf_edges[(key[0], key[1], str(action["seed_id"]), str(action["neighbor_id"]))]["features"]["seed_rank"])
        mechanisms["NF004"].extend(action_rows)
        rows.append({"corpus": "NF004", "key": f"{key[0]}:{key[1]}", "group": nf_meta[key][0],
                     "DIRECT": gold <= direct, "CONTROL": control, "TREATMENT": treatment,
                     "recovered_chars": selection["treatment"]["recovered_chars"],
                     "missing_control": sorted(missing), "carried_missing": sorted(missing & added_links),
                     "admitted": action_rows})

    records = {record.question_id: record
               for record in adapt_population(longmem_path, _population_ids(population_path))}
    for question_id in sorted(long_selections):
        selection, record = long_selections[question_id], records[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        direct = set().union(*(identities[value] for value in selection["direct_ids"]))
        control_links = _delivered(selection["baseline_actions"], identities)
        added = selection["treatment"]["additions"]
        added_links = _delivered(added, identities)
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        missing = gold - (direct | control_links)
        control, treatment = gold <= direct | control_links, gold <= direct | control_links | added_links
        if control and not treatment:
            raise DA023AnalysisError("DA-023 LongMem control loss")
        if treatment and not control and not missing <= added_links:
            raise DA023AnalysisError("DA-023 LongMem gain lacks carrier")
        action_rows = _action_rows(added, identities, missing,
                                   lambda action: long_edges[question_id][str(action["neighbor_id"])]["seed_rank"])
        mechanisms["LONGMEM"].extend(action_rows)
        rows.append({"corpus": "LONGMEM", "key": question_id, "group": record.question_type,
                     "DIRECT": gold <= direct, "CONTROL": control, "TREATMENT": treatment,
                     "recovered_chars": selection["treatment"]["recovered_chars"],
                     "missing_control": sorted(missing), "carried_missing": sorted(missing & added_links),
                     "admitted": action_rows})

    corpora = {}
    expected = {"NF004": (1_098, 935, 970), "LONGMEM": (465, 164, 188)}
    for corpus, anchor in expected.items():
        subset = [row for row in rows if row["corpus"] == corpus]
        complete = {arm: sum(row[arm] for row in subset) for arm in ("DIRECT", "CONTROL", "TREATMENT")}
        if (len(subset), complete["DIRECT"], complete["CONTROL"]) != anchor:
            raise DA023AnalysisError(f"DA-023 {corpus} control differs")
        groups = {}
        for group in sorted({row["group"] for row in subset}):
            cell = [row for row in subset if row["group"] == group]
            groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                             "contrast": paired(cell)}
        actions = mechanisms[corpus]
        decisive = [row for row in actions if row["carries_missing"]]
        corpora[corpus] = {"n": len(subset), "complete": complete, "contrast": paired(subset),
                           "by_group": groups, "one_hop_ceiling": 986 if corpus == "NF004" else 250,
                           "mechanism": {"recovered_chars": distribution([row["recovered_chars"] for row in subset]),
                                         "admitted_actions": len(actions), "decisive_actions": len(decisive),
                                         "admitted_cost": distribution([row["cost"] for row in actions]),
                                         "decisive_cost": distribution([row["cost"] for row in decisive]),
                                         "admitted_seed_rank": distribution([row["seed_rank"] for row in actions]),
                                         "decisive_seed_rank": distribution([row["seed_rank"] for row in decisive]),
                                         "decisive_position": distribution([row["position"] for row in decisive])}}
    signal = all(cell["contrast"]["gains"] >= 5 and cell["contrast"]["losses"] == 0 and
                 all(group["contrast"]["net"] >= 0 for group in cell["by_group"].values())
                 for cell in corpora.values())
    result = {"schema": "da023-backreference-result-v1",
              "status": "BACKREFERENCE_DELIVERY_SIGNAL" if signal else "NO_BACKREFERENCE_DELIVERY_SIGNAL",
              "corpora": corpora, "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent exact availability; backreference reader use and runtime unvalidated"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(locomo_path: Path, longmem_path: Path, population_path: Path,
                 selection_path: Path, nf_edge_path: Path, long_edge_path: Path,
                 output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(locomo_path, longmem_path, population_path, selection_path, nf_edge_path, long_edge_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da023-result-") as directory:
        replay_result, replay_rows = analyze(locomo_path, longmem_path, population_path, selection_path, nf_edge_path, long_edge_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA023AnalysisError("DA-023 result replay differs")
    return result


__all__ = ["DA023AnalysisError", "analyze", "paired", "run_analysis"]

