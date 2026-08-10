"""Study 011 section 4: the binding offline pre-test.

Six gates run here. All are offline, consume committed candidate
identities, make zero model and zero embedding calls, and are enforced
rather than narrated. Any failure stops the study.

G1  Arm A: the recency tier is active and the K tier is truly disabled.
G2  Arm B: the similarity tier is active alone.
G3  Arm C: both tiers reach the window together. The gate that would
    have caught eleven studies.
G4  Arm B's delivered set is not a subset of Arm A's. Two tiers that
    return the same episodes are one tier.
G5  Arm D reproduces the committed deployed result on identity and
    payload digest, not on counts.
G7  Every probe's required facts are planted strictly before the probe.

G6, the 35-turn ablation, is live and is not part of this module.

**What these gates are measured on.** Study 011's arms are live runs
whose stores do not exist yet, and section 4 requires the pre-test to
pass *before* any live run is authorized. The gates therefore replay all
four arms against the corrected Tier 6 run's committed candidates, the
same store the section 4.1 ceiling was measured on. They certify that
each arm's configuration delivers what it claims to deliver on a real
store. They do not certify the arms' own stores, which do not exist yet.
Section 3.1 records the same boundary for G5.

T is 6 of 13, locked in `decisions/DECISION_T_threshold.md`. "Delivers a
K episode" means the K path delivered an episode the recency path would
not have carried anyway; that decision records why the other reading
makes G1 fail by construction.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.analysis.ic001_internal_packing import (
    ModelCallGuard,
    _normalize,
    q11_availability,
)
from src.analysis.retrieval_bakeoff_tier6_121 import (
    ATOMIC_ITEMS,
    TARGETED_ITEMS,
)
from src.analysis.study_011_achievability import (
    ARM_LABEL,
    ARMS,
    BUDGET_CHARS,
    PROBE_TURNS,
    QUESTION_TURNS,
    SCRIPT,
    STUDY_ROOT,
    AchievabilityError,
    _git,
    _hash_paths,
    _input_paths,
    _provider_model_loaded,
    _repo_relative,
    _sha256,
    _state_for_arm,
    _write_artifact_manifest,
    _write_json,
    assert_probe_map,
    assert_source_configuration,
    load_context_records,
    load_episodes,
)
from src.internal_packing.ic001 import pack_arm, path_accounting

COMMITTED_A0 = (
    STUDY_ROOT.parent
    / "components"
    / "retrieval_mechanism_ledger"
    / "artifacts"
    / "e005"
    / "a0_baseline.json"
)
T_DECISION = STUDY_ROOT / "decisions" / "DECISION_T_threshold.md"
Q11_TURN = 120
T = 6
GATES = ("G1", "G2", "G3", "G4", "G5", "G7")


class GateFailure(RuntimeError):
    """Raised when a binding gate does not pass. The study stops."""


# --------------------------------------------------------------------------
# Shared replay
# --------------------------------------------------------------------------


def replay_arms(records: dict[int, dict], by_id: dict[str, dict]) -> dict:
    """Pack every arm at every probe window, once, for all gates."""

    replay: dict[str, dict[int, dict]] = {arm: {} for arm in ARMS}
    for turn in PROBE_TURNS:
        record = records[turn]
        recency_candidates = set(record["n_candidate_ids"])
        k_candidates = list(record["k_candidate_ids"])
        k_only_candidates = [
            identifier
            for identifier in k_candidates
            if identifier not in recency_candidates
        ]
        for arm in ARMS:
            _recency_on, _k_on, order = ARMS[arm]
            state = _state_for_arm(arm=arm, record=record, by_id=by_id)
            packed = pack_arm(state, arm=order, budget=BUDGET_CHARS)
            accounting = path_accounting(state, packed)
            delivered = set(packed.selected_ids)
            replay[arm][turn] = {
                "delivered_ids": sorted(delivered),
                "payload": packed.payload,
                "serialized_chars": packed.serialized_chars,
                "payload_sha256": packed.payload_sha256,
                "selected_ids": list(packed.selected_ids),
                "recency_delivered": accounting["episodes_by_path"]["recency"],
                "k_delivered": sum(
                    1 for i in k_candidates if i in delivered
                ),
                "k_only_delivered": sorted(
                    i for i in k_only_candidates if i in delivered
                ),
            }
    return replay


def _questions_at(turns: list[int]) -> list[str]:
    return sorted(
        question for question, turn in QUESTION_TURNS.items() if turn in turns
    )


def _both_units(turns: list[int]) -> dict:
    questions = _questions_at(turns)
    return {
        "windows": sorted(turns),
        "window_count": len(turns),
        "questions": questions,
        "question_count": len(questions),
    }


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


def g1_stm_isolation(replay: dict) -> dict:
    arm = replay["A"]
    without_recency = [
        turn for turn in PROBE_TURNS if arm[turn]["recency_delivered"] < 1
    ]
    with_k = [turn for turn in PROBE_TURNS if arm[turn]["k_only_delivered"]]
    return {
        "gate": "G1",
        "arm": "A",
        "label": ARM_LABEL["A"],
        "requirement": (
            ">=1 recency episode at every probe window and 0 K-path "
            "episodes at every probe window"
        ),
        "windows_without_a_recency_episode": without_recency,
        "windows_with_a_k_path_episode": with_k,
        "certifies": "the recency tier is active and the K tier is truly disabled",
        "status": "PASS" if not without_recency and not with_k else "FAIL",
    }


def g2_ltm_isolation(replay: dict) -> dict:
    arm = replay["B"]
    reached = [turn for turn in PROBE_TURNS if arm[turn]["k_only_delivered"]]
    with_recency = [
        turn for turn in PROBE_TURNS if arm[turn]["recency_delivered"] > 0
    ]
    delivery = _both_units(reached)
    return {
        "gate": "G2",
        "arm": "B",
        "label": ARM_LABEL["B"],
        "requirement": f">=1 K episode at >=T of 13 probes (T = {T}) and 0 recency episodes anywhere",
        "T": T,
        "delivery": delivery,
        "windows_with_a_recency_episode": with_recency,
        "certifies": "the similarity tier is active alone",
        "status": (
            "PASS"
            if delivery["question_count"] >= T and not with_recency
            else "FAIL"
        ),
    }


def g3_joint_delivery(replay: dict) -> dict:
    arm = replay["C"]
    both = [
        turn
        for turn in PROBE_TURNS
        if arm[turn]["k_only_delivered"] and arm[turn]["recency_delivered"] > 0
    ]
    delivery = _both_units(both)
    return {
        "gate": "G3",
        "arm": "C",
        "label": ARM_LABEL["C"],
        "requirement": f">=1 episode from each path at >=T of 13 probes (T = {T})",
        "T": T,
        "delivery": delivery,
        "certifies": "both tiers reach the window together",
        "note": (
            "The gate eleven studies did not run. Under the deployed order "
            "the same measurement gives the comparison recorded below."
        ),
        "deployed_order_for_comparison": _both_units(
            [
                turn
                for turn in PROBE_TURNS
                if replay["D"][turn]["k_only_delivered"]
                and replay["D"][turn]["recency_delivered"] > 0
            ]
        ),
        "status": "PASS" if delivery["question_count"] >= T else "FAIL",
    }


def g4_path_non_identity(replay: dict) -> dict:
    """Two tiers returning the same episodes are one tier.

    Reported with the overlap fraction, because a non-subset that differs
    by one trivial episode would pass while the paths are substantially
    the same (section 7).
    """

    rows = []
    non_subset = []
    for turn in PROBE_TURNS:
        b_set = set(replay["B"][turn]["delivered_ids"])
        a_set = set(replay["A"][turn]["delivered_ids"])
        overlap = b_set & a_set
        is_subset = bool(b_set) and b_set <= a_set
        if b_set and not is_subset:
            non_subset.append(turn)
        rows.append(
            {
                "probe_turn": turn,
                "arm_b_delivered": len(b_set),
                "arm_a_delivered": len(a_set),
                "overlap": len(overlap),
                "overlap_fraction": (
                    round(len(overlap) / len(b_set), 4) if b_set else None
                ),
                "arm_b_is_subset_of_arm_a": is_subset,
            }
        )
    delivery = _both_units(non_subset)
    return {
        "gate": "G4",
        "requirement": f"Arm B's delivered set is not a subset of Arm A's at >=T of 13 probes (T = {T})",
        "T": T,
        "delivery": delivery,
        "per_window": rows,
        "certifies": "the two paths select different material",
        "status": "PASS" if delivery["question_count"] >= T else "FAIL",
    }


def g5_deployed_reproduction(replay: dict) -> dict:
    """Identity and digest, never counts.

    A fact count can match on entirely different episodes, so every
    assertion below is on identity or on the serialized payload itself.
    The target is section 3.1's: the corrected Tier 6 run's turn-120
    candidate order re-packed at the enforced budget, not that run's
    delivered window.
    """

    committed = json.loads(COMMITTED_A0.read_text(encoding="utf-8"))
    packed = replay["D"][Q11_TURN]
    q11 = q11_availability(packed["payload"])

    committed_items = {
        (row["domain"], row["item"]): bool(row["available"])
        for row in committed["items"]
    }
    # The committed artifact carries the item rows, not a rolled-up
    # per-domain count, so the breakdown is derived from the same rows
    # the item-level check reads.
    committed_per_domain = {domain: 0 for domain, _i, _n, _t in ATOMIC_ITEMS}
    for row in committed["items"]:
        if row["available"]:
            committed_per_domain[row["domain"]] += 1
    replay_items = {
        (row["domain"], row["item"]): bool(row["available"])
        for row in q11["items"]
    }
    mismatches = sorted(
        f"{domain}:{item}"
        for (domain, item), value in committed_items.items()
        if replay_items.get((domain, item)) != value
    )

    checks = {
        "fact_count": q11["fact_count"] == committed["fact_count"],
        "domain_count": q11["domain_count"] == committed["domain_count"],
        "per_domain_breakdown": q11["per_domain"] == committed_per_domain,
        "item_level_match": not mismatches,
        "selected_episode_count": (
            len(packed["selected_ids"]) == committed["selected_episode_count"]
        ),
        "episode_identities": (
            list(packed["selected_ids"]) == list(committed["selected_ids"])
        ),
        "serialized_chars": (
            packed["serialized_chars"] == committed["serialized_chars"]
        ),
        "payload_sha256": (
            packed["payload_sha256"] == committed["payload_sha256"]
        ),
        "budget_matches": committed["budget_chars"] == BUDGET_CHARS,
    }
    return {
        "gate": "G5",
        "arm": "D",
        "label": ARM_LABEL["D"],
        "requirement": "Arm D reproduces the committed deployed result exactly",
        "committed_artifact": _repo_relative(COMMITTED_A0),
        "committed_artifact_sha256": _sha256(COMMITTED_A0),
        "target_is": (
            "the corrected Tier 6 run's turn-120 candidate order re-packed "
            "at the enforced 32,000-character budget; not that run's "
            "delivered window, which was 60,285 characters at budget 60,595 "
            "(pre-registration section 3.1)"
        ),
        "certifies": "harness fidelity, offline; not that a live Arm D reproduces anything",
        "checks": checks,
        "item_mismatches": mismatches,
        "committed": {
            "fact_count": committed["fact_count"],
            "domain_count": committed["domain_count"],
            "per_domain": committed_per_domain,
            "selected_episode_count": committed["selected_episode_count"],
            "selected_ids": list(committed["selected_ids"]),
            "serialized_chars": committed["serialized_chars"],
            "payload_sha256": committed["payload_sha256"],
        },
        "replay": {
            "fact_count": q11["fact_count"],
            "domain_count": q11["domain_count"],
            "per_domain": q11["per_domain"],
            "selected_episode_count": len(packed["selected_ids"]),
            "selected_ids": list(packed["selected_ids"]),
            "serialized_chars": packed["serialized_chars"],
            "payload_sha256": packed["payload_sha256"],
        },
        "consequence_on_failure": "Study 011 stops; every arm's accounting is uninterpretable",
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def g7_probe_order() -> dict:
    """Every probe's required facts planted strictly before the probe.

    Checked against the script text rather than against a hand-kept table
    of plant turns, so a table that drifts from the corpus cannot pass
    this. Study 010 is the failure this catches.
    """

    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    user_turns = {
        int(turn["turn"]): _normalize(turn["user"]) for turn in script["turns"]
    }

    def first_plant(needle: str) -> int | None:
        for turn in sorted(user_turns):
            if needle in user_turns[turn]:
                return turn
        return None

    rows = []
    violations = []
    for question, (probe_turn, needles) in TARGETED_ITEMS.items():
        for needle in needles:
            planted = first_plant(needle)
            ok = planted is not None and planted < probe_turn
            rows.append(
                {
                    "question": question,
                    "probe_turn": probe_turn,
                    "needle": needle,
                    "first_planted_turn": planted,
                    "planted_before_probe": ok,
                }
            )
            if not ok:
                violations.append(f"{question}:{needle}")

    for domain, item, needle, plant_turns in ATOMIC_ITEMS:
        planted = first_plant(needle)
        ok = planted is not None and planted < Q11_TURN
        # Drift means the key names a plant turn whose text does not
        # contain the needle. An *earlier* occurrence is not drift: a
        # term can be mentioned in passing before the turn that plants
        # it canonically, which only makes the fact available sooner.
        present_at_declared = all(
            needle in user_turns.get(turn, "") for turn in plant_turns
        )
        rows.append(
            {
                "question": "Q11",
                "probe_turn": Q11_TURN,
                "needle": needle,
                "first_planted_turn": planted,
                "planted_before_probe": ok,
                "declared_plant_turns": list(plant_turns),
                "needle_present_at_declared_turns": present_at_declared,
                "earlier_mention_than_declared": (
                    planted is not None and planted < min(plant_turns)
                ),
            }
        )
        if not ok:
            violations.append(f"Q11:{domain}:{item}")

    drifted = [
        row
        for row in rows
        if row.get("declared_plant_turns")
        and not row["needle_present_at_declared_turns"]
    ]
    return {
        "gate": "G7",
        "requirement": "every probe's required facts planted in a scripted user turn strictly before the probe turn",
        "script": _repo_relative(SCRIPT),
        "checked_needles": len(rows),
        "violations": violations,
        "declared_plant_turn_drift": [
            {
                "needle": row["needle"],
                "declared": row["declared_plant_turns"],
                "script": row["first_planted_turn"],
            }
            for row in drifted
        ],
        "earlier_mentions_than_declared": [
            {
                "needle": row["needle"],
                "declared": row["declared_plant_turns"],
                "first_in_script": row["first_planted_turn"],
            }
            for row in rows
            if row.get("earlier_mention_than_declared")
        ],
        "rows": rows,
        "certifies": "no probe requires a fact the corpus never planted",
        "status": "PASS" if not violations and not drifted else "FAIL",
    }


# --------------------------------------------------------------------------
# Run
# --------------------------------------------------------------------------


def run(output_root: Path) -> dict:
    inputs = _hash_paths([*_input_paths(), COMMITTED_A0, T_DECISION])
    loaded_before = _provider_model_loaded()

    with ModelCallGuard() as guard:
        records = load_context_records()
        by_id = load_episodes()
        configuration = assert_source_configuration(records)
        probe_map = assert_probe_map()
        replay = replay_arms(records, by_id)
        results = {
            "G1": g1_stm_isolation(replay),
            "G2": g2_ltm_isolation(replay),
            "G3": g3_joint_delivery(replay),
            "G4": g4_path_non_identity(replay),
            "G5": g5_deployed_reproduction(replay),
            "G7": g7_probe_order(),
        }
        audit = guard.audit()

    loaded_after = _provider_model_loaded()
    call_free = (
        not audit["attempted_calls"]
        and loaded_after == loaded_before
        and bool(audit["guarded_entry_points"])
    )
    audit = {
        **audit,
        "status": "PASS" if call_free else "FAIL",
        "amendment_001": "not applicable to Study 011",
        "embedding_provider_model_loaded_before": loaded_before,
        "embedding_provider_model_loaded_after": loaded_after,
        "this_run_loaded_a_model": loaded_after and not loaded_before,
    }
    if not call_free:
        raise GateFailure(f"model or embedding call attempted: {audit}")

    output_dir = output_root / "pre_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    for gate, result in results.items():
        _write_json(output_dir / f"{gate.lower()}.json", result)

    failed = [gate for gate, result in results.items() if result["status"] != "PASS"]
    summary = {
        "study": "011",
        "section": "4",
        "T": T,
        "t_decision": _repo_relative(T_DECISION),
        "budget_chars": BUDGET_CHARS,
        "source_run_configuration": configuration,
        "probe_map": probe_map,
        "gates": {gate: results[gate]["status"] for gate in GATES},
        "failed_gates": failed,
        "measured_on": (
            "the corrected Tier 6 run's committed candidates. These gates "
            "certify each arm's configuration on a real store; the arms' "
            "own stores do not exist until the live runs."
        ),
        "status": "PASS" if not failed else "FAIL",
        "consequence_on_failure": "any failure stops the study",
    }
    _write_json(output_dir / "pre_test_summary.json", summary)
    _write_json(output_dir / "no_model_call_audit.json", audit)
    _write_json(output_dir / "run_header.json", _run_header(inputs, summary))
    _write_artifact_manifest(output_dir)

    if failed:
        raise GateFailure(f"binding gates failed: {failed}")
    return summary


def _run_header(inputs: dict[str, str], summary: dict) -> dict:
    pre_registration = STUDY_ROOT / "pre_registration.md"
    return {
        "study": "011",
        "artifact": "section 4 binding offline pre-test",
        "pre_registration_sha256": _sha256(pre_registration),
        "design_commit": _git("rev-list", "-1", "HEAD", "--", str(pre_registration)),
        "execution_commit": _git("rev-parse", "HEAD"),
        "source_worktree_clean": not _git(
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            "src",
            "scripts",
            "tests",
            "episodic",
            str(pre_registration),
        ),
        "T": T,
        "budget_chars": BUDGET_CHARS,
        "input_sha256": inputs,
        "packer": "src/internal_packing/ic001.py, imported unchanged",
        "model_calls": 0,
        "embedding_calls": 0,
        "gates": summary["gates"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=STUDY_ROOT / "gates",
    )
    args = parser.parse_args(argv)
    try:
        summary = run(args.output_root)
    except (GateFailure, AchievabilityError) as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1
    for gate, status in summary["gates"].items():
        print(f"{gate}: {status}")
    print(f"pre-test: {summary['status']} (T = {summary['T']})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
