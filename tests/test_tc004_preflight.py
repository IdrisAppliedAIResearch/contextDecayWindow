"""Constructed-store tests for TC-004's pair-to-turn transfer mechanism."""

from __future__ import annotations

import numpy as np
import pytest

from analysis.locomo_nf_development import PairCandidate
from analysis.tc001_exploration import Episode
from analysis.tc004_preflight import (
    ChildUnit,
    ParentUnit,
    TC004PreflightError,
    mixed_context,
)
from episodic._render import render_episode_element, render_stm_payload


def _parent(index: int, *, singleton: bool = False) -> ParentUnit:
    pair = PairCandidate(
        identity=f"p{index}",
        sample_id="conv",
        session_id="session_1",
        session_order=0,
        pair_order=index,
        text=f"speaker: parent {index}\nother: reply {index}",
        chars=20,
        dialog_ids=(f"d{index}a",) if singleton else (f"d{index}a", f"d{index}b"),
    )
    record = {
        "id": pair.identity,
        "turn_number": index + 1,
        "user_message": f"speaker: parent {index}",
        "assistant_message": f"other: reply {index}",
        "ground_truth_domain": pair.session_id,
        "embedding": np.ones(1024, dtype=np.float32),
    }
    episode = Episode(record, pair, len(render_episode_element(record)))
    children = []
    for offset, dialog_id in enumerate(pair.dialog_ids):
        child_record = {
            "id": f"c{index}{offset}",
            "turn_number": f"{index + 1}.{offset}",
            "user_message": f"child {index} {offset}",
            "assistant_message": "",
            "ground_truth_domain": pair.session_id,
        }
        children.append(
            ChildUnit(
                identity=str(child_record["id"]),
                dialog_id=dialog_id,
                parent_index=index,
                offset=offset,
                text=str(child_record["user_message"]),
                record=child_record,
                element_chars=len(render_episode_element(child_record)),
            )
        )
    return ParentUnit(index, episode, tuple(children))


def test_zero_splits_offer_the_exact_parent_records() -> None:
    parents = (_parent(0), _parent(1))
    packed = mixed_context(
        parents,
        {"p0": 0.9, "p1": 0.1},
        {},
        (),
        100_000,
    )
    assert packed.selected_ids == ("p0", "p1")
    assert packed.delivered_dialog_ids == frozenset(
        {"d0a", "d0b", "d1a", "d1b"}
    )


def test_a_split_replaces_its_parent_and_children_use_own_scores() -> None:
    parents = (_parent(0), _parent(1))
    packed = mixed_context(
        parents,
        {"p0": 0.9, "p1": 0.5},
        {"c00": 0.1, "c01": 0.8},
        (0,),
        100_000,
    )
    assert packed.selected_ids == ("c01", "p1", "c00")
    assert "p0" not in packed.selected_ids


def test_renderer_cost_can_make_one_child_fit_without_its_sibling() -> None:
    parent = _parent(0)
    first = parent.children[0]
    budget = len(render_stm_payload([], [first.record]))
    packed = mixed_context(
        (parent,),
        {"p0": 0.1},
        {"c00": 0.9, "c01": 0.1},
        (0,),
        budget,
    )
    assert packed.selected_ids == ("c00",)
    assert packed.delivered_dialog_ids == frozenset({"d0a"})


def test_singletons_are_not_fake_split_trials() -> None:
    with pytest.raises(TC004PreflightError):
        mixed_context(
            (_parent(0, singleton=True),),
            {"p0": 0.1},
            {"c00": 0.2},
            (0,),
            10_000,
        )


def test_missing_or_nonfinite_scores_fail_closed() -> None:
    parent = _parent(0)
    with pytest.raises(TC004PreflightError):
        mixed_context((parent,), {}, {}, (), 10_000)
    with pytest.raises(TC004PreflightError):
        mixed_context((parent,), {"p0": float("nan")}, {}, (), 10_000)
