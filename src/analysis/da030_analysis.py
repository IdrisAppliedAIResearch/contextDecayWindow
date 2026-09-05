"""Exact cross-corpus evidence analysis for DA-030 composition."""

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

SELECTION_SHA256 = "cd69a0887cf2564d5929b7ee34947568f579327f86224ab9a88b1f77b0e52c2a"
AUDIT_SHA256 = "2bd5cbea6702a8714928a69b30fba02c054bf7229e141568540f1964716b9029"


class DA030AnalysisError(RuntimeError):
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
        raise DA030AnalysisError("LongMem population differs")
    return frozenset(str(row["question_id"])
                     for row in json.loads(path.read_text(encoding="utf-8"))["rows"])


def _delivered(actions: Sequence[Mapping[str, Any]], identities: Mapping[str, Sequence[str]]) -> set[str]:
    output = set()
    for action in actions:
        if action["kind"] == "PAIR":
            output.update(identities[str(action["neighbor_id"])])
        elif action["kind"] in {"TURN", "MEMBER"}:
            output.add(identities[str(action["neighbor_id"])][int(action["member"])])
    return output


def analyze(locomo_path: Path, longmem_path: Path, population_path: Path,
            selection_path: Path, audit_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if sha256_file(selection_path) != SELECTION_SHA256 or sha256_file(audit_path) != AUDIT_SHA256:
        raise DA030AnalysisError("Sealed input differs")
    selections = list(read_gzip(selection_path))
    blockers = {f"{row['corpus']}:{row['key']}": row["blocker"] for row in read_gzip(audit_path)}
    nf_selections = {(str(row["comparison_key"]), int(row["duplicate_ordinal"])): row
                     for row in selections if row["corpus"] == "NF004"}
    long_selections = {str(row["question_id"]): row for row in selections if row["corpus"] == "LONGMEM"}
    nf_evidence, nf_pairs, nf_meta = {}, {}, {}
    for record in adapt_split(locomo_path, HOLDOUT_IDS):
        for source in record.candidates:
            nf_pairs[source.candidate.identity] = tuple(source.dialogue_ids)
        for question in record.questions:
            key = (question.comparison_key, question.duplicate_ordinal)
            nf_evidence[key] = set(question.resolved_dialogue_ids)
            nf_meta[key] = question.sample_id
    rows = []
    for key in sorted(nf_selections):
        selection, gold = nf_selections[key], nf_evidence[key]
        direct = set().union(*(nf_pairs[value] for value in selection["direct_ids"]))
        base = (direct | _delivered(selection["baseline_actions"], nf_pairs)
                | _delivered(selection["da023"]["additions"], nf_pairs)
                | _delivered(selection["control"]["actions"], nf_pairs))
        treatment_set = base | _delivered(selection["treatment"]["actions"], nf_pairs)
        control, treatment = gold <= base, gold <= treatment_set
        if control and not treatment:
            raise DA030AnalysisError("NF protected control loss")
        item_key = f"{key[0]}:{key[1]}"
        rows.append({"corpus": "NF004", "key": item_key, "group": nf_meta[key],
                     "CONTROL": control, "TREATMENT": treatment,
                     "blocker": blockers.get(f"NF004:{item_key}"),
                     "actions": selection["treatment"]["actions"]})
    records = {record.question_id: record
               for record in adapt_population(longmem_path, _population_ids(population_path))}
    for question_id in sorted(long_selections):
        selection, record = long_selections[question_id], records[question_id]
        identities = {episode.candidate.identity: tuple(episode.turn_identities) for episode in record.episodes}
        gold = {turn.candidate.identity for turn in record.turns if turn.is_target}
        direct = set().union(*(identities[value] for value in selection["direct_ids"]))
        base = (direct | _delivered(selection["baseline_actions"], identities)
                | _delivered(selection["da023"]["additions"], identities)
                | _delivered(selection["control"]["actions"], identities))
        treatment_set = base | _delivered(selection["treatment"]["actions"], identities)
        control, treatment = gold <= base, gold <= treatment_set
        if control and not treatment:
            raise DA030AnalysisError("LongMem protected control loss")
        rows.append({"corpus": "LONGMEM", "key": question_id, "group": record.question_type,
                     "CONTROL": control, "TREATMENT": treatment,
                     "blocker": blockers.get(f"LONGMEM:{question_id}"),
                     "actions": selection["treatment"]["actions"]})
    corpora = {}
    expected = {"NF004": (1098, 977), "LONGMEM": (465, 208)}
    for corpus, anchor in expected.items():
        subset = [row for row in rows if row["corpus"] == corpus]
        complete = {arm: sum(row[arm] for row in subset) for arm in ("CONTROL", "TREATMENT")}
        if (len(subset), complete["CONTROL"]) != anchor:
            raise DA030AnalysisError(f"{corpus} control anchor differs")
        groups = {}
        for group in sorted({row["group"] for row in subset}):
            cell = [row for row in subset if row["group"] == group]
            groups[group] = {"n": len(cell), "complete": {arm: sum(row[arm] for row in cell) for arm in complete},
                             "contrast": paired(cell)}
        gains = [row for row in subset if not row["CONTROL"] and row["TREATMENT"]]
        admitted = [action for row in subset for action in row["actions"] if action["kind"] == "MEMBER"]
        corpora[corpus] = {"n": len(subset), "complete": complete, "contrast": paired(subset),
                           "by_group": groups, "one_hop_ceiling": 986 if corpus == "NF004" else 250,
                           "mechanism": {"admitted_members": len(admitted),
                                         "member_cost": distribution([action["cost"] for action in admitted]),
                                         "member_position": distribution([action["position"] for action in admitted]),
                                         "gain_blockers": {name: sum(row["blocker"] == name for row in gains)
                                                           for name in sorted({row["blocker"] for row in gains if row["blocker"]})}}}
    valid = {corpus: cell["contrast"]["losses"] == 0 and
             all(group["contrast"]["net"] >= 0 for group in cell["by_group"].values())
             for corpus, cell in corpora.items()}
    if corpora["NF004"]["contrast"]["gains"] >= 2 and corpora["LONGMEM"]["contrast"]["gains"] >= 5 and all(valid.values()):
        status = "COMPACT_ATOMIC_COMPOSITION_SIGNAL"
    elif any(corpora[corpus]["contrast"]["gains"] >= 2 and valid[corpus] for corpus in corpora):
        status = "PARTIAL_COMPACT_ATOMIC_SIGNAL"
    else:
        status = "NO_COMPACT_ATOMIC_COMPOSITION_SIGNAL"
    result = {"schema": "da030-compact-atomic-result-v1", "status": status,
              "corpora": corpora, "calls": {"embedding": 0, "model": 0, "cache_access": 0},
              "claim_boundary": "spent exact availability; reader use and runtime unvalidated"}
    return result, rows


def _write(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as output:
            for row in rows:
                output.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())


def run_analysis(locomo_path: Path, longmem_path: Path, population_path: Path,
                 selection_path: Path, audit_path: Path, output_dir: Path) -> dict[str, Any]:
    result, rows = analyze(locomo_path, longmem_path, population_path, selection_path, audit_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "outcomes.jsonl.gz"
    _write(path, rows)
    with tempfile.TemporaryDirectory(prefix="da030-result-") as directory:
        replay_result, replay_rows = analyze(locomo_path, longmem_path, population_path, selection_path, audit_path)
        replay = Path(directory) / path.name
        _write(replay, replay_rows)
        identical = result == replay_result and path.read_bytes() == replay.read_bytes()
    result.update({"replay_byte_identical": identical, "outcomes_sha256": sha256_file(path)})
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not identical:
        raise DA030AnalysisError("Result replay differs")
    return result


__all__ = ["DA030AnalysisError", "analyze", "paired", "run_analysis"]

