"""Blind context construction and gates for HH-004."""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from analysis.da006_reserved_links import _member_maps
from analysis.da013_preflight import sha256_file
from analysis.hh002_run import _read_json, _write_json
from analysis.nf004_anatomy_features import load_blind_cases

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "experiments" / "comparisons" / "hh_004"
RUN = BASE / "artifacts" / "run"
PREFLIGHT = BASE / "artifacts" / "preflight"
DATASET = Path(r"C:\Users\muzaf\Downloads\locomo10.json")
SELECTION = (REPO / "experiments" / "components" / "biological_memory"
             / "da_098" / "artifacts" / "preflight" / "blind_allocations.jsonl.gz")
HH003_CONTEXTS = (REPO / "experiments" / "comparisons" / "hh_003"
                  / "artifacts" / "run" / "A_EPISODIC" / "contexts.json")
ARM = "A_DA098_ARCH32_DECODED"
EXPECTED = 842
SELECTION_SHA256 = "f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9"

CONTROL_FILES = {
    "A_EPISODIC.predictions": ("hh_003/artifacts/run/A_EPISODIC/predictions.json", "54726a6bada60f33ab0fe9b0b3074cf6cb200a6a8da0ba9f9ce8a4c34bd4ec77"),
    "A_EPISODIC.judged": ("hh_003/artifacts/run/A_EPISODIC/judged_r1.json", "7a63d1be617ef737b6fc507b1888cfed7858d4a88a05df85b078e08bf821d020"),
    "A_EPISODIC_ASPECT.predictions": ("hh_003/artifacts/run/A_EPISODIC_ASPECT/predictions.json", "b71cfc7b1d855f0770e2fc8686125da1f820e879da0e166a2644c1517e423145"),
    "A_EPISODIC_ASPECT.judged": ("hh_003/artifacts/run/A_EPISODIC_ASPECT/judged_r1.json", "aefc8e91bd602c6449e0b5fa038b9c815070291b36024faecae937e46536ffc7"),
    "A_CDW.predictions": ("hh_002/artifacts/A_CDW/predictions.json", "37601e42b9f24fb6a6d01d78911f2b33a7a0554b568fff1151d3964353ae5628"),
    "A_CDW.judged": ("hh_002/artifacts/A_CDW/judged_r1.json", "367210a4b6aa37c763db23abd46a33810b6953bdb92be291146f8b8277d9d3cc"),
    "A_RAG.predictions": ("hh_002/artifacts/A_RAG/predictions.json", "bc49bb20a6172dcfa68e3ef825487c776674afaf0f95e19cf9509d4dcaea68af"),
    "A_RAG.judged": ("hh_002/artifacts/A_RAG/judged_r1.json", "dd3ff262f3a1b27fc22a445c2f578676974c547a2eca6df1120f5cbe9a24c374"),
    "A_FULL.predictions": ("hh_002/artifacts/A_FULL/predictions.json", "a6f82d0ed63eedb3aa1c84472c7ac978e5db6e5c8d5323cdf23ecbc712a150c9"),
    "A_FULL.judged": ("hh_002/artifacts/A_FULL/judged_r1.json", "467521c8e972d3728fac93b772ab453b3708f4d26607ecba16e1062e6ee6649a"),
}


class HH004GateError(RuntimeError):
    pass


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _read_selections() -> list[dict[str, Any]]:
    if sha256_file(SELECTION) != SELECTION_SHA256:
        raise HH004GateError("DA-098 selection differs")
    with gzip.open(SELECTION, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def render_members(values: list[dict[str, str]]) -> str:
    chunks = ["<retrieved_memory>"]
    for index, member in enumerate(values, start=1):
        chunks.extend((f'<member index="{index}">',
                       f'{member["speaker"]}: {member["text"]}', "</member>"))
    chunks.append("</retrieved_memory>")
    return "\n".join(chunks)


def build_contexts() -> dict[str, Any]:
    hh_items = (_read_json(HH003_CONTEXTS) or {}).get("items", {})
    by_source = {(str(row["sample_id"]), int(row["source_index"])): (key, row)
                 for key, row in hh_items.items()}
    cases = load_blind_cases(DATASET)
    members, _ = _member_maps(DATASET, cases)
    items: dict[str, dict[str, Any]] = {}
    for selection in _read_selections():
        source_key = (str(selection["sample_id"]), int(selection["source_index"]))
        prior = by_source.get(source_key)
        if prior is None:
            continue
        key, hh = prior
        selected = [(str(identity), int(member))
                    for identity, member in selection["arch32"]["selected_members"]]
        payload = [members[identity][member] for identity, member in selected]
        context = render_members(payload)
        order_sha = hashlib.sha256("\0".join(
            f"{identity}:{member}" for identity, member in selected
        ).encode()).hexdigest()
        items[key] = {
            "key": key, "sample_id": source_key[0], "source_index": source_key[1],
            "category": int(hh["category"]), "question": str(hh["question"]),
            "answer": str(hh["answer"]), "context": context,
            "context_chars": len(context), "units_delivered": len(selected),
            "search_time": 0.0,
            "detail": {
                "allocation_sha256": SELECTION_SHA256,
                "selected_order_sha256": order_sha,
                "selected_members": len(selected),
                "decoded": True,
                "compact_wire_test": False,
            },
        }
    if len(items) != EXPECTED:
        raise HH004GateError(f"HH-004 population is {len(items)}/{EXPECTED}")
    counts: dict[str, int] = {}
    for item in items.values():
        counts[item["sample_id"]] = counts.get(item["sample_id"], 0) + 1
    expected_counts = {"conv-26": 151, "conv-30": 81, "conv-43": 177,
                       "conv-44": 123, "conv-49": 153, "conv-50": 157}
    if counts != expected_counts:
        raise HH004GateError(f"HH-004 conversation cells differ: {counts}")
    return {"schema": "hh004-contexts-v1", "arm": ARM,
            "allocation_sha256": SELECTION_SHA256,
            "population": len(items), "conversation_counts": counts,
            "items": dict(sorted(items.items()))}


def verify_controls(items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    result = {}
    expected = {(row["sample_id"], int(row["source_index"])): row
                for row in items.values()}
    root = REPO / "experiments" / "comparisons"
    for name, (relative, expected_hash) in CONTROL_FILES.items():
        path = root / relative
        observed = sha256_file(path)
        if observed != expected_hash:
            raise HH004GateError(f"{name} hash differs")
        records = {(str(row["sample_id"]), int(row["source_index"])): row
                   for row in (_read_json(path) or {}).get("records", [])}
        joined = expected.keys() & records.keys()
        if len(joined) != EXPECTED:
            raise HH004GateError(f"{name} does not join 842 rows")
        for identity in joined:
            row, source = records[identity], expected[identity]
            if "question" in row and str(row["question"]) != source["question"]:
                raise HH004GateError(f"{name} question differs")
            if "answer" in row and str(row["answer"]) != source["answer"]:
                raise HH004GateError(f"{name} answer differs")
        result[name] = {"sha256": observed, "joined": EXPECTED}
    return result


def run_preflight() -> dict[str, Any]:
    contexts = build_contexts()
    replay = build_contexts()
    if contexts != replay:
        raise HH004GateError("HH-004 context replay differs")
    path = RUN / ARM / "contexts.json"
    _write_json(path, contexts)
    controls = verify_controls(contexts["items"])
    chars = [item["context_chars"] for item in contexts["items"].values()]
    paid_runner = Path(__file__).with_name("hh004_run.py")
    supervisor = Path(__file__).with_name("hh004_supervisor.py")
    result = {
        "schema": "hh004-preflight-v1", "status": "PASS",
        "population": EXPECTED, "contexts_sha256": sha256_file(path),
        "context_chars": {"min": min(chars), "max": max(chars)},
        "byte_identical_replay": True, "controls": controls,
        "selection_sha256": SELECTION_SHA256,
        "runner_sha256": sha256_file(Path(__file__)),
        "paid_runner_sha256": sha256_file(paid_runner),
        "supervisor_sha256": sha256_file(supervisor),
        "preregistration_commit": _git("rev-parse", "32b6c6d9"),
    }
    _write_json(PREFLIGHT / "g0_g3.json", result)
    return result


def assert_paid_preconditions() -> dict[str, Any]:
    gate = _read_json(PREFLIGHT / "g0_g3.json") or {}
    contexts = RUN / ARM / "contexts.json"
    if gate.get("status") != "PASS" or gate.get("contexts_sha256") != sha256_file(contexts):
        raise HH004GateError("committed HH-004 context gate differs")
    if gate.get("runner_sha256") != sha256_file(Path(__file__)):
        raise HH004GateError("HH-004 context runner differs")
    if gate.get("paid_runner_sha256") != sha256_file(Path(__file__).with_name("hh004_run.py")):
        raise HH004GateError("HH-004 paid runner differs")
    if gate.get("supervisor_sha256") != sha256_file(Path(__file__).with_name("hh004_supervisor.py")):
        raise HH004GateError("HH-004 supervisor differs")
    if _git("status", "--porcelain", "--untracked-files=no"):
        raise HH004GateError("tracked worktree is dirty before paid submission")
    if not _git("ls-files", str((PREFLIGHT / "g0_g3.json").relative_to(REPO))):
        raise HH004GateError("HH-004 G0-G3 is not committed")
    return gate


__all__ = ["ARM", "BASE", "EXPECTED", "PREFLIGHT", "RUN", "HH004GateError",
           "assert_paid_preconditions", "build_contexts", "run_preflight"]
