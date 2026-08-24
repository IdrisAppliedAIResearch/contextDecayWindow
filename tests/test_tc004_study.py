from __future__ import annotations

import ast

import numpy as np

from analysis.tc004_mechanism import (
    exact_incremental_pack,
    offered_units,
    policy_order,
    predictor_scores,
    select,
    split_count,
)
from analysis.tc004_preflight import ChildUnit, ParentUnit
from analysis.tc004_study import average_precision, disposition, mechanism_violations
from analysis.tc001_exploration import Episode
from analysis.locomo_nf_development import PairCandidate
from episodic._packing import pack_stm_payload
from episodic._render import render_episode_element


def _parents() -> tuple[ParentUnit, ...]:
    parents = []
    for index, lengths in enumerate(((80, 110), (20, 30), (200,))):
        pair = PairCandidate(
            identity=f"parent-{index}", sample_id="conv", session_id="session_1",
            session_order=0, pair_order=index, text="\n".join("x" * n for n in lengths),
            chars=sum(lengths) + len(lengths) - 1,
            dialog_ids=tuple(f"d-{index}-{offset}" for offset in range(len(lengths))),
        )
        parent_record = {"id": pair.identity, "turn_number": index + 1, "user_message": "u", "assistant_message": "a", "ground_truth_domain": "session_1", "embedding": np.ones(1024, dtype=np.float32)}
        children = []
        for offset, length in enumerate(lengths):
            record = {"id": f"child-{index}-{offset}", "turn_number": f"{index + 1}.{offset}", "user_message": "x" * length, "assistant_message": "", "ground_truth_domain": "session_1"}
            children.append(ChildUnit(record["id"], pair.dialog_ids[offset], index, offset, "x" * length, record, len(render_episode_element(record))))
        parents.append(ParentUnit(index, Episode(parent_record, pair, len(render_episode_element(parent_record))), tuple(children)))
    return tuple(parents)


def test_incremental_packer_is_exact_committed_packer() -> None:
    parents = _parents()
    parent_scores = {f"parent-{index}": 0.9 - index * 0.1 for index in range(3)}
    child_scores = {child.identity: 0.95 - child.parent_index * 0.1 - child.offset * 0.01 for parent in parents for child in parent.children}
    for split in ((), (0,), (1,), (0, 1)):
        ranked = offered_units(parents, parent_scores, child_scores, split)
        for budget in (0, 35, 100, 250, 10_000):
            fast = exact_incremental_pack(ranked, budget)
            direct = pack_stm_payload([], [unit.record for unit in ranked], budget)
            assert fast.selected_ids == direct.selected_ids
            assert fast.serialized_chars == len(direct.payload)
            import hashlib
            assert fast.payload_sha256 == hashlib.sha256(direct.payload.encode("utf-8")).hexdigest()


def test_split_replaces_parent_and_singleton_never_splits() -> None:
    parents = _parents()
    ps = {f"parent-{index}": 0.5 for index in range(3)}
    cs = {child.identity: 0.5 for parent in parents for child in parent.children}
    offered = offered_units(parents, ps, cs, (0,))
    identities = {unit.identity for unit in offered}
    assert "parent-0" not in identities
    assert {"child-0-0", "child-0-1"} <= identities
    assert "parent-2" in identities


def test_predictors_and_source_order_ties_are_stable() -> None:
    parents = _parents()
    ps = {f"parent-{index}": 0.4 for index in range(3)}
    cs = {child.identity: 0.6 for parent in parents for child in parent.children}
    scores = predictor_scores(parents, ps, cs, "x")
    assert set(scores) == {"embedding_localization_gain", "length", "lexical_localization_gain"}
    assert policy_order(parents, {0: 1.0, 1: 1.0}) == (0, 1)
    assert split_count(0.01, 1297) == 13
    assert split_count(0.0, 1297) == 0
    assert split_count(1.0, 1297) == 1297


def test_average_precision_and_dispositions() -> None:
    assert average_precision((0, 1, 2), frozenset({0, 2})) == (1.0 + 2 / 3) / 2
    controls = {"positive_exists": True, "adverse_exists": True}
    base = {"ap_evaluable_questions": 6, "mean_embedding_ap": .5, "mean_length_ap": .4}
    assert disposition({**base, "gains": 6, "losses": 0, "one_sided_exact_p": .015625}, controls) == "OPERATIONAL_TEST_WORKS"
    assert disposition({**base, "gains": 4, "losses": 1, "one_sided_exact_p": .1875}, controls) == "CARRIES_SIGNAL"
    assert disposition({**base, "gains": 1, "losses": 1, "one_sided_exact_p": .75}, controls) == "NO_PREDICTIVE_SIGNAL"
    assert disposition({**base, "ap_evaluable_questions": 5, "gains": 5, "losses": 0, "one_sided_exact_p": .03125}, controls) == "INSTRUMENT_INADEQUATE"


def test_mechanism_leakage_plants_are_rejected() -> None:
    clean = "import math\nvalue = candidate.score\n"
    assert not mechanism_violations(clean)
    assert mechanism_violations(clean + "value = question.resolved_evidence_ids\n")
    assert mechanism_violations(clean + "from analysis.tc004_study import outcome\n")
    ast.parse(clean)
