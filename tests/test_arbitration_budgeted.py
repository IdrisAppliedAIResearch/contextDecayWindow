"""Study 007 S7_003 — containment dedup, refill, floor protection, assembly."""

import pytest

from src.memory.arbitration import arbitrate_budgeted, arbitrate_candidates
from src.memory.retrieval_budget import PHASE_FILL, PHASE_FLOOR


def stm(episode_id: str, similarity: float = 0.6, chars: int = 200) -> dict:
    return {
        "id": episode_id,
        "topic_id": "civil",
        "topic_label": "civil",
        "similarity": similarity,
        "user_message": "",
        "assistant_message": "s" * chars,
        "turn_number": 1,
    }


def ltm(
    episode_id: str,
    topic: str,
    similarity: float,
    chars: int = 200,
    distilled_id: str | None = None,
) -> dict:
    return {
        "id": episode_id,
        "distilled_id": distilled_id or f"d-{episode_id}",
        "topic_id": topic,
        "topic_label": topic,
        "similarity": similarity,
        "user_message": "",
        "assistant_message": "l" * chars,
        "turn_number": 2,
        "dream_event": 31,
        "event_type": "transition",
        "source_turns": [2],
    }


# --------------------------------------------------------------------------
# S7-T-009 — containment dedup and refill
# --------------------------------------------------------------------------


def test_span_whose_source_episode_is_in_stm_is_dropped():
    result = arbitrate_budgeted(
        stm_candidates=[stm("ep1")],
        ltm_candidates=[ltm("ep1", "civil", 0.90), ltm("ep2", "civil", 0.10)],
        stm_block_episode_ids={"ep1"},
        ltm_budget=10_000,
        ltm_k_min=1,
    )

    ltm_ids = {
        e["id"] for e in result.episodes if e["provenance"] in {"ltm", "both"}
    }
    assert ltm_ids == {"ep2"}
    assert result.containment_drops == 1


def test_containment_drop_frees_budget_for_a_replacement():
    """The dropped episode's budget must be reused, not lost."""
    candidates = [
        ltm("ep1", "civil", 0.90, chars=400),
        ltm("ep2", "civil", 0.80, chars=400),
        ltm("ep3", "civil", 0.70, chars=400),
    ]
    without = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=800, ltm_k_min=0
    )
    assert {e["id"] for e in without.episodes} == {"ep1", "ep2"}

    with_drop = arbitrate_budgeted(
        [], candidates, {"ep1"}, ltm_budget=800, ltm_k_min=0
    )
    assert {e["id"] for e in with_drop.episodes} == {"ep2", "ep3"}
    assert with_drop.containment_drops == 1
    assert with_drop.budget.chars_used == 800


def test_floor_survives_a_containment_drop_from_its_own_topic():
    """A dropped floor selection is replaced from the same topic, not lost."""
    candidates = [
        ltm("civil-0", "civil", 0.95),
        ltm("marine-0", "marine", 0.30),
        ltm("marine-1", "marine", 0.20),
    ]
    result = arbitrate_budgeted(
        [], candidates, {"marine-0"}, ltm_budget=10_000, ltm_k_min=1
    )

    topics = {e["topic_id"] for e in result.episodes}
    assert topics == {"civil", "marine"}
    assert result.budget.floor_per_topic["marine"] == 1
    assert "marine-1" in {e["id"] for e in result.episodes}


def test_containment_never_admits_a_dropped_episode_as_floor():
    """Guards the assertion inside arbitrate_budgeted."""
    candidates = [ltm("ep1", "solo", 0.9), ltm("ep2", "solo", 0.8)]
    result = arbitrate_budgeted(
        [], candidates, {"ep1"}, ltm_budget=10_000, ltm_k_min=3
    )
    assert "ep1" not in result.budget.floor_ids


def test_no_containment_hits_leaves_selection_unchanged():
    candidates = [ltm("ep1", "civil", 0.9), ltm("ep2", "art", 0.5)]
    result = arbitrate_budgeted(
        [stm("other")], candidates, {"other"}, ltm_budget=10_000, ltm_k_min=1
    )
    assert result.containment_drops == 0
    assert result.refills == 0
    assert len(result.budget.selected) == 2


def test_identifier_dedup_still_collapses_repeated_records():
    """Carried from Study 004: two records of one episode render once."""
    candidates = [
        ltm("ep1", "civil", 0.90, distilled_id="d-a"),
        ltm("ep1", "civil", 0.80, distilled_id="d-b"),
    ]
    result = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=10_000, ltm_k_min=0
    )

    assert len(result.episodes) == 1
    assert result.budget.collapsed_to_episode == 1


def test_budget_is_respected_after_containment_and_refill():
    candidates = [ltm(f"ep{i}", "civil", 0.9 - i * 0.01, chars=300) for i in range(20)]
    result = arbitrate_budgeted(
        [], candidates, {"ep0", "ep3", "ep7"}, ltm_budget=1500, ltm_k_min=2
    )
    assert result.budget.chars_used <= 1500
    assert {"ep0", "ep3", "ep7"}.isdisjoint({e["id"] for e in result.episodes})


# --------------------------------------------------------------------------
# S7-T-010 — assembly, floor protection, STM untouched
# --------------------------------------------------------------------------


def test_floor_selection_is_never_evicted_by_ranking():
    """A floor pick with the lowest similarity in the set must survive."""
    candidates = [
        ltm(f"civil-{i}", "civil", 0.90 - i * 0.001) for i in range(30)
    ] + [ltm("marine-0", "marine", 0.001)]

    result = arbitrate_budgeted(
        [stm(f"s{i}", 0.99) for i in range(10)],
        candidates,
        set(),
        ltm_budget=100_000,
        ltm_k_min=1,
    )

    assert "marine-0" in {e["id"] for e in result.episodes}
    assert result.budget.phases["marine-0"] == PHASE_FLOOR


def test_stm_contributes_exactly_what_it_was_given():
    stm_candidates = [stm(f"s{i}", 0.7 - i * 0.01) for i in range(6)]
    result = arbitrate_budgeted(
        stm_candidates,
        [ltm("ep1", "civil", 0.99)],
        set(),
        ltm_budget=10_000,
        ltm_k_min=1,
    )

    stm_ids = {
        e["id"] for e in result.episodes if e["provenance"] in {"stm", "both"}
    }
    assert stm_ids == {c["id"] for c in stm_candidates}
    assert result.stm_candidates == 6


def test_provenance_marks_an_episode_present_in_both_tiers():
    result = arbitrate_budgeted(
        [stm("shared", 0.5)],
        [ltm("shared", "civil", 0.9)],
        set(),  # not in the STM *block*, so containment does not apply
        ltm_budget=10_000,
        ltm_k_min=1,
    )

    assert len(result.episodes) == 1
    assert result.episodes[0]["provenance"] == "both"
    assert result.episodes[0]["dream_event"] == 31


def test_ltm_metadata_survives_the_merge():
    """The tagged renderer needs distilled provenance on a 'both' episode."""
    result = arbitrate_budgeted(
        [stm("shared")],
        [ltm("shared", "civil", 0.9, distilled_id="d-keep")],
        set(),
        ltm_budget=10_000,
        ltm_k_min=1,
    )
    episode = result.episodes[0]
    assert episode["distilled_id"] == "d-keep"
    assert episode["source_turns"] == [2]


def test_final_set_has_no_duplicate_ids():
    result = arbitrate_budgeted(
        [stm("a"), stm("b")],
        [ltm("a", "civil", 0.9), ltm("c", "art", 0.4)],
        set(),
        ltm_budget=10_000,
        ltm_k_min=1,
    )
    ids = [e["id"] for e in result.episodes]
    assert len(ids) == len(set(ids))


def test_no_ltm_count_cap_is_applied():
    """The departure from Study 004: LTM size is set by budget, not by k_stm+M."""
    candidates = [ltm(f"e{i}", f"t{i % 4}", 0.9 - i * 0.001, chars=100) for i in range(40)]
    result = arbitrate_budgeted(
        [], candidates, set(), ltm_budget=4000, ltm_k_min=1
    )
    assert result.ltm_episodes_in_final_set == 40
    assert result.budget.chars_used == 4000


def test_empty_ltm_yields_stm_only():
    result = arbitrate_budgeted(
        [stm("a")], [], set(), ltm_budget=16_000, ltm_k_min=3
    )
    assert [e["provenance"] for e in result.episodes] == ["stm"]
    assert result.budget.topics_present == []


def test_carried_count_based_arbitration_is_unchanged():
    """Study 007 must not alter the control arm's policy."""
    stm_candidates = [stm("a", 0.9), stm("b", 0.8)]
    ltm_candidates = [ltm("c", "civil", 0.7), ltm("d", "art", 0.6)]

    result = arbitrate_candidates(
        stm_candidates, ltm_candidates, k_stm=2, ltm_top_m=5
    )

    assert [e["id"] for e in result.episodes] == ["a", "b", "c", "d"]
    assert result.budget is None
    assert result.containment_drops == 0
