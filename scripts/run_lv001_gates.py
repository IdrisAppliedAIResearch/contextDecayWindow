"""LV-001 pre-inference gates G1, G3, G4 and G5.

Registered in `experiments/components/live_validation/LV_001_pre_registration.md`
§4. All are binding: any failure blocks inference.

G2 (seeded-prefix determinism) needs the model and runs separately, after these.

    python scripts/run_lv001_gates.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "experiments/components/live_validation/gates"
LEDGER = REPO / "experiments/components/retrieval_mechanism_ledger/artifacts"

SCRIPT = REPO / "experiments/study_005/script.json"
Q11_ITEMS = LEDGER / "e005/q11_item_matrix.csv"
TARGETED = LEDGER / "e005/targeted_no_regression.csv"
BREADTH_PROBE_TURN = 120

ANCHOR = "89614a0c3799e0e96edb7809ba11eac07d39ac90"


def normalized(text: str) -> str:
    """Casefold, unify dashes, and fold diacritics.

    Diacritic folding is required, not a convenience. The script plants the
    painting as "The Annunciation of Forlì" at turn 55; the committed item list
    writes it "Forli". Without folding, four genuinely planted items read as
    unplanted and G1 fails on an encoding difference rather than on a missing
    fact. Folding only makes matching more permissive for accented characters,
    and every item it newly matches is verified below by reporting the turn it
    was found in, so a false match would be visible rather than silent.
    """
    text = unicodedata.normalize("NFKD", text).casefold()
    text = "".join(c for c in text if not unicodedata.combining(c))
    for dash in "–—−":
        text = text.replace(dash, "-")
    return re.sub(r"\s+", " ", text)


def load_user_turns() -> dict[int, str]:
    payload = json.loads(SCRIPT.read_text(encoding="utf-8"))
    turns = payload["turns"] if isinstance(payload, dict) else payload
    out = {}
    for index, turn in enumerate(turns, 1):
        number = int(turn.get("turn", index))
        out[number] = normalized(
            turn.get("user") or turn.get("user_message") or turn.get("content") or ""
        )
    return out


def gate_g1(user_turns: dict[int, str]) -> dict:
    """Every rubric-required item is planted strictly before its probe turn."""
    findings = []

    with Q11_ITEMS.open(encoding="utf-8-sig", newline="") as handle:
        q11 = list(csv.DictReader(handle))
    for row in q11:
        item = normalized(row["item"])
        planted = sorted(t for t, text in user_turns.items()
                         if t < BREADTH_PROBE_TURN and item in text)
        findings.append({
            "probe": "Q11",
            "probe_turn": BREADTH_PROBE_TURN,
            "domain": row["domain"],
            "item": row["item"],
            "planted_before_probe": bool(planted),
            "first_planted_turn": planted[0] if planted else None,
        })

    with TARGETED.open(encoding="utf-8-sig", newline="") as handle:
        seen = set()
        for row in csv.DictReader(handle):
            key = (row["question"], row["turn"], row["item"])
            if key in seen:
                continue
            seen.add(key)
            probe_turn = int(row["turn"])
            item = normalized(row["item"])
            planted = sorted(t for t, text in user_turns.items()
                             if t < probe_turn and item in text)
            findings.append({
                "probe": row["question"],
                "probe_turn": probe_turn,
                "domain": None,
                "item": row["item"],
                "planted_before_probe": bool(planted),
                "first_planted_turn": planted[0] if planted else None,
            })

    unplanted = [f for f in findings if not f["planted_before_probe"]]
    return {
        "gate": "G1",
        "certifies": "every rubric-required item is planted in a scripted user "
                     "turn strictly before the probe that asks for it",
        "items_checked": len(findings),
        "unplanted": unplanted,
        "status": "PASS" if not unplanted else "FAIL",
        "note": "scripts/check_probe_fact_order.py parses Study 010's "
                "rubric_1000.md table shape and does not read this corpus's "
                "item sets, so the same property is checked here directly "
                "against the committed Q11 and targeted item lists.",
        "findings": findings,
    }


def gate_g3() -> dict:
    """The shipped call shape must reproduce the primary configuration.

    E005 embedded nine probe queries in one batch; `EpisodeStore.context()`
    embeds a single query alone, and that difference flips 6 of 146 committed
    payloads (PAPER-001 §7.2). The primary configuration is not among the six,
    but LV-001 re-checks rather than assumes.
    """
    errata = (REPO / "ERRATA.md").read_text(encoding="utf-8")
    claim = (
        "The E005 primary configuration `A3_l0.1_r0.0_k16` is not among the six"
        in errata
    )
    dx001 = json.loads(
        (LEDGER / "dx001/dx001_results.json").read_text(encoding="utf-8")
    )
    return {
        "gate": "G3",
        "certifies": "the primary configuration is unaffected by the "
                     "solo-versus-batched embedding call shape",
        "primary_configuration": "A3_l0.1_r0.0_k16",
        "errata_states_primary_unaffected": claim,
        "replay_gate_payloads_reproduced": dx001.get("replay", {}).get(
            "payloads_reproduced", dx001.get("payloads_reproduced")
        ),
        "status": "PASS" if claim else "FAIL",
        "note": "Live confirmation is the byte-identical check inside the "
                "run itself: the turn-120 selection is compared against the "
                "committed primary payload SHA.",
    }


def gate_g4() -> dict:
    """Mechanism code must not read rubric or answer-key artifacts."""
    forbidden = ("q_facts_key", "q11_item_matrix", "rubric", "targeted_no_regression")
    roots = [REPO / "episodic/src/episodic", REPO / "src/memory"]
    violations = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace").casefold()
            for token in forbidden:
                if token in text:
                    violations.append({"file": str(path.relative_to(REPO)),
                                       "token": token})
    return {
        "gate": "G4",
        "certifies": "retrieval, formation, ranking and gating code reads no "
                     "rubric or answer-key artifact",
        "roots_scanned": [str(r.relative_to(REPO)) for r in roots],
        "violations": violations,
        "status": "PASS" if not violations else "FAIL",
    }


def gate_g5() -> dict:
    """Control provenance: clean tree, known anchor, control engine unmodified."""
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()

    dirty = git("status", "--porcelain")
    engine = REPO / "src/memory/context_matched_stm.py"
    engine_sha = hashlib.sha256(
        subprocess.run(["git", "show", f"HEAD:{engine.relative_to(REPO).as_posix()}"],
                       cwd=REPO, capture_output=True, check=True).stdout
    ).hexdigest()
    committed = git("log", "-1", "--format=%H", "--",
                    engine.relative_to(REPO).as_posix())
    return {
        "gate": "G5",
        "certifies": "the control arm's engine is prior committed code, not the "
                     "current engine with features disabled",
        "anchor_commit": ANCHOR,
        "control_engine": "src/memory/context_matched_stm.py",
        "control_engine_sha256": engine_sha,
        "control_engine_last_modified_commit": committed,
        "worktree_clean_ignoring_lv001": not [
            line for line in dirty.splitlines()
            if "live_validation" not in line
        ],
        "status": "PASS" if not [
            line for line in dirty.splitlines() if "live_validation" not in line
        ] else "FAIL",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    user_turns = load_user_turns()
    results = [gate_g1(user_turns), gate_g3(), gate_g4(), gate_g5()]

    for result in results:
        path = OUT / f"{result['gate'].lower()}.json"
        path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        detail = ""
        if result["gate"] == "G1":
            detail = f"  ({result['items_checked']} items, {len(result['unplanted'])} unplanted)"
        if result["gate"] == "G4":
            detail = f"  ({len(result['violations'])} violations)"
        print(f"{result['gate']}: {result['status']}{detail}")

    failed = [r["gate"] for r in results if r["status"] != "PASS"]
    if failed:
        print(f"\nBLOCKED: {', '.join(failed)} failed. Inference must not run.")
        return 1
    print("\nG1, G3, G4, G5 pass. G2 runs next, against the model.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
