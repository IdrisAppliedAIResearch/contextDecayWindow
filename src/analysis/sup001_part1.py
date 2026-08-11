from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from src.analysis.sup001_benchmark import REPO_ROOT, STUDY_ROOT, canonical_digest
from src.analysis.sup001_control import CONTROL_PATH
from src.analysis.sup001_vectors import MANIFEST_PATH, MECHANISM_PATH, sha256_file
from src.biological_memory.supersession import SupersessionError, SupersessionLedger


PART1_ROOT = STUDY_ROOT / "artifacts" / "sup001_part1"
PART1_PATH = PART1_ROOT / "part1.json"


def build_ledger(mechanism: dict[str, Any]) -> tuple[SupersessionLedger, list[dict[str, Any]]]:
    ledger = SupersessionLedger()
    transitions: list[dict[str, Any]] = []
    for index, row in enumerate(mechanism["registrations"], start=1):
        if row["operation"] == "initial":
            ledger.register_initial(row["memory_key"], row["episode_sha256"])
        elif row["operation"] == "update":
            ledger.register_update(
                row["memory_key"],
                row["episode_sha256"],
                supersedes=row["supersedes"],
            )
        else:
            raise AssertionError(f"Unknown registration operation: {row['operation']}")
        transitions.append(
            {
                "step": index,
                "operation": row["operation"],
                "memory_key": row["memory_key"],
                "episode_sha256": row["episode_sha256"],
                "supersedes": row["supersedes"],
                "distribution": ledger.validate(),
            }
        )
    return ledger, transitions


def ledger_digest(ledger: SupersessionLedger) -> str:
    return canonical_digest(ledger.to_dict())


def _expect_failure(name: str, operation: Callable[[], None]) -> dict[str, str]:
    try:
        operation()
    except SupersessionError as error:
        return {"case": name, "status": "PASS", "error": str(error)}
    raise AssertionError(f"Degenerate state did not fail closed: {name}")


def failure_witnesses(mechanism: dict[str, Any], ledger: SupersessionLedger) -> list[dict[str, str]]:
    registrations = mechanism["registrations"]
    first = registrations[0]
    second_key = next(row for row in registrations if row["memory_key"] != first["memory_key"])
    first_lineage = ledger.lineage(first["memory_key"])
    second_lineage = ledger.lineage(second_key["memory_key"])
    new_identity = hashlib.sha256(b"sup001 failure witness").hexdigest()

    def duplicate() -> None:
        candidate = SupersessionLedger.from_dict(ledger.to_dict())
        candidate.register_initial(first["memory_key"], first["episode_sha256"])

    def unknown_parent() -> None:
        candidate = SupersessionLedger.from_dict(ledger.to_dict())
        candidate.register_update(
            first["memory_key"], new_identity, supersedes="f" * 64
        )

    def cross_key() -> None:
        candidate = SupersessionLedger.from_dict(ledger.to_dict())
        candidate.register_update(
            first["memory_key"], new_identity, supersedes=second_lineage[-1].episode_sha256
        )

    def fork() -> None:
        candidate = SupersessionLedger.from_dict(ledger.to_dict())
        candidate.register_update(
            first["memory_key"], new_identity, supersedes=first_lineage[0].episode_sha256
        )

    def corrupt(field: str, value: Any, index: int = 0) -> None:
        payload = copy.deepcopy(ledger.to_dict())
        payload["lineages"][first["memory_key"]][index][field] = value
        SupersessionLedger.from_dict(payload)

    def duplicate_candidate() -> None:
        identity = first_lineage[-1].episode_sha256
        ledger.natural_rank(
            [
                {"episode_sha256": identity, "cosine": 0.5},
                {"episode_sha256": identity, "cosine": 0.4},
            ],
            limit=1,
        )

    return [
        _expect_failure("duplicate identity/key", duplicate),
        _expect_failure("unknown parent", unknown_parent),
        _expect_failure("cross-key edge", cross_key),
        _expect_failure("fork from non-leaf", fork),
        _expect_failure("cycle", lambda: corrupt("supersedes", first_lineage[-1].episode_sha256)),
        _expect_failure("zero accessible leaves", lambda: corrupt("accessibility", 0.0, -1)),
        _expect_failure("multiple accessible leaves", lambda: corrupt("accessibility", 1.0, 0)),
        _expect_failure("duplicate retrieval candidate", duplicate_candidate),
    ]


def read_purity(
    mechanism: dict[str, Any], control: dict[str, Any], ledger: SupersessionLedger
) -> dict[str, Any]:
    before = ledger_digest(ledger)
    natural_first = [
        ledger.natural_rank(row["population"], limit=8) for row in control["queries"]
    ]
    lineages_first = {
        row["memory_key"]: [record.episode_sha256 for record in ledger.lineage(row["memory_key"])]
        for row in mechanism["registrations"]
        if row["operation"] == "initial"
    }
    middle = ledger_digest(ledger)
    natural_second = [
        ledger.natural_rank(row["population"], limit=8) for row in control["queries"]
    ]
    lineages_second = {
        key: [record.episode_sha256 for record in ledger.lineage(key)]
        for key in lineages_first
    }
    after = ledger_digest(ledger)
    return {
        "query_count": len(natural_first),
        "lineage_count": len(lineages_first),
        "natural_reads_identity_equal": natural_first == natural_second,
        "lineage_reads_identity_equal": lineages_first == lineages_second,
        "state_digest_before": before,
        "state_digest_middle": middle,
        "state_digest_after": after,
        "state_unchanged": before == middle == after,
    }


def reconstruction_digest(mechanism_path: Path = MECHANISM_PATH) -> dict[str, Any]:
    mechanism = json.loads(mechanism_path.read_text(encoding="utf-8"))
    ledger, transitions = build_ledger(mechanism)
    return {
        "mechanism_digest": canonical_digest(mechanism),
        "ledger_digest": ledger_digest(ledger),
        "transition_digest": canonical_digest(transitions),
        "transition_count": len(transitions),
        "final_distribution": ledger.validate(),
    }


def run_part1(output_path: Path = PART1_PATH) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite SUP-001 Part 1: {output_path}")
    mechanism = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    vector_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ledger, transitions = build_ledger(mechanism)
    local = reconstruction_digest()
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_sup001_part1.py"),
        "--digest-only",
    ]
    fresh = json.loads(subprocess.check_output(command, cwd=REPO_ROOT, text=True))
    purity = read_purity(mechanism, control, ledger)
    failures = failure_witnesses(mechanism, ledger)
    episode_hashes_before = [row["episode_sha256"] for row in mechanism["episodes"]]
    vector_hashes = [row["vector_sha256"] for row in vector_manifest["vectors"] if row["kind"] == "episode"]
    payload = {
        "study": "SUP-001",
        "stage": "Preflight Part 1 label-blind exploration",
        "status": "PASS",
        "behavioral_identity": "Explicit registration creates reciprocal old-to-new lineages; natural reads exclude non-leaves, lineage reads bypass accessibility, and reads do not mutate state.",
        "inputs": {
            "mechanism_sha256": sha256_file(MECHANISM_PATH),
            "control_sha256": sha256_file(CONTROL_PATH),
            "vector_manifest_sha256": sha256_file(MANIFEST_PATH),
            "episode_count": len(mechanism["episodes"]),
            "registration_count": len(mechanism["registrations"]),
            "query_count": len(mechanism["queries"]),
        },
        "transitions": transitions,
        "final_distribution": ledger.validate(),
        "ledger": ledger.to_dict(),
        "read_purity": purity,
        "degenerate_states": failures,
        "fresh_process": {
            "command": command,
            "local": local,
            "fresh": fresh,
            "identity_equal": local == fresh,
        },
        "immutability": {
            "store_episode_count": len(episode_hashes_before),
            "unique_episode_hashes": len(set(episode_hashes_before)),
            "episode_hash_sequence_sha256": canonical_digest(episode_hashes_before),
            "episode_vector_count": len(vector_hashes),
            "episode_vector_hash_sequence_sha256": canonical_digest(vector_hashes),
            "text_or_vector_rewrite_operations": 0,
        },
        "not_reached": {
            "sealed_measurement_key": "not opened",
            "T1_measurement": "requires committed Part 1, final design lock, and passing PF1-PF10",
        },
    }
    checks = (
        local == fresh,
        purity["natural_reads_identity_equal"],
        purity["lineage_reads_identity_equal"],
        purity["state_unchanged"],
        all(row["status"] == "PASS" for row in failures),
        ledger.validate() == {
            "record_count": 192,
            "lineage_count": 64,
            "accessible_count": 64,
            "silent_count": 128,
        },
        len(episode_hashes_before) == len(set(episode_hashes_before)) == 256,
        len(vector_hashes) == 256,
    )
    if not all(checks):
        payload["status"] = "FAIL"
        raise AssertionError("SUP-001 Part 1 failed")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload
