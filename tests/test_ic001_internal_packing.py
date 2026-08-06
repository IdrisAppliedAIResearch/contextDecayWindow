import json

import pytest

from episodic._packing import EMPTY_PAYLOAD_CHARS, pack_stm_payload
from episodic._render import render_stm_payload
from src.analysis.ic001_internal_packing import (
    b0_gate,
    leakage_audit,
    paired_comparison,
    verdict,
)
from src.internal_packing.ic001 import (
    PACKING_ORDERS,
    IC001Error,
    TierState,
    assert_b0_matches_deployed_packer,
    assert_mechanism_path_allowed,
    build_tier_state,
    dropped_by_path,
    pack_arm,
    path_accounting,
)


def episode(identifier: str, turn: int, size: int = 80) -> dict:
    return {
        "id": identifier,
        "turn_number": turn,
        "user_message": "u" * size,
        "assistant_message": "a" * size,
    }


def state(recency, k_hits, coverage=(), probe_turn: int = 120) -> TierState:
    return TierState(
        probe_turn=probe_turn,
        recency=tuple(recency),
        k_hits=tuple(k_hits),
        coverage=tuple(coverage),
    )


# --------------------------------------------------------------------------
# The single variable
# --------------------------------------------------------------------------


def test_b0_reproduces_the_deployed_packer_byte_for_byte() -> None:
    recency = [episode(f"n{index}", 100 + index) for index in range(6)]
    k_hits = [episode("k1", 40), episode("k2", 41)]
    tiers = state(recency, k_hits)
    budget = len(render_stm_payload(recency[:4], []))

    packed = pack_arm(tiers, arm="B0", budget=budget)
    deployed = pack_stm_payload(recency, k_hits, budget)

    assert packed.payload == deployed.payload
    assert packed.selected_ids == tuple(deployed.selected_ids)
    assert (
        assert_b0_matches_deployed_packer(tiers, packed, budget=budget)["status"]
        == "PASS"
    )


def test_k_first_admits_the_k_episode_the_deployed_order_starves() -> None:
    recency = [episode(f"n{index}", 100 + index) for index in range(6)]
    k_hits = [episode("k1", 40)]
    tiers = state(recency, k_hits)
    budget = len(render_stm_payload(recency[:3], []))

    b0 = pack_arm(tiers, arm="B0", budget=budget)
    b1 = pack_arm(tiers, arm="B1", budget=budget)

    assert "k1" not in b0.selected_ids
    assert "k1" in b1.selected_ids
    assert b0.serialized_chars <= budget
    assert b1.serialized_chars <= budget


def test_only_the_order_differs_between_the_arms() -> None:
    recency = [episode(f"n{index}", 100 + index) for index in range(4)]
    k_hits = [episode("k1", 40)]
    tiers = state(recency, k_hits)
    generous = 200_000

    b0 = pack_arm(tiers, arm="B0", budget=generous)
    b1 = pack_arm(tiers, arm="B1", budget=generous)

    # With room for everything the two orders deliver the same window.
    assert set(b0.selected_ids) == set(b1.selected_ids)
    assert b0.payload == b1.payload
    assert b0.considered_ids != b1.considered_ids
    assert PACKING_ORDERS["B0"][:2] == ("recency", "k")
    assert PACKING_ORDERS["B1"][:2] == ("k", "recency")


def test_a_k_recency_overlap_is_considered_at_k_priority_but_renders_as_recent() -> None:
    shared = episode("shared", 105)
    recency = [episode("n0", 100), shared]
    tiers = state(recency, [shared, episode("k1", 40)])

    packed = pack_arm(tiers, arm="B1", budget=200_000)

    assert packed.considered_ids[0] == "shared"
    assert "shared" in {str(item["id"]) for item in packed.recent_episodes}
    assert "shared" not in {str(item["id"]) for item in packed.stm_episodes}
    assert len(packed.selected_ids) == len(set(packed.selected_ids))


# --------------------------------------------------------------------------
# Carried packing policy
# --------------------------------------------------------------------------


def test_overflow_skips_rather_than_stops_in_both_arms() -> None:
    big = episode("big", 100, size=4_000)
    small_a = episode("small_a", 101, size=10)
    small_b = episode("small_b", 102, size=10)
    tiers = state([big, small_a, small_b], [])
    budget = len(render_stm_payload([small_a, small_b], []))

    for arm in ("B0", "B1"):
        packed = pack_arm(tiers, arm=arm, budget=budget)
        assert packed.selected_ids == ("small_a", "small_b")
        assert packed.dropped_ids == ("big",)


def test_budget_below_the_empty_payload_delivers_nothing() -> None:
    tiers = state([episode("n0", 100)], [episode("k0", 40)])
    packed = pack_arm(tiers, arm="B1", budget=EMPTY_PAYLOAD_CHARS - 1)
    assert packed.payload == ""
    assert packed.selected_ids == ()
    assert set(packed.dropped_ids) == {"n0", "k0"}


def test_unregistered_arm_is_refused() -> None:
    with pytest.raises(IC001Error):
        pack_arm(state([], []), arm="B2", budget=1_000)


def test_missing_committed_identity_is_refused() -> None:
    with pytest.raises(IC001Error):
        build_tier_state(
            probe_turn=120,
            n_candidate_ids=["absent"],
            k_candidate_ids=[],
            by_id={},
        )


# --------------------------------------------------------------------------
# Path accounting
# --------------------------------------------------------------------------


def test_path_characters_and_overhead_sum_to_the_payload() -> None:
    recency = [episode("n0", 100), episode("n1", 101)]
    k_hits = [episode("k0", 40)]
    coverage = [episode("c0", 20)]
    tiers = state(recency, k_hits, coverage)

    packed = pack_arm(tiers, arm="B1", budget=200_000)
    accounting = path_accounting(tiers, packed)

    assert (
        accounting["element_chars_total"] + accounting["overhead_chars"]
        == packed.serialized_chars
    )
    assert accounting["episodes_by_path"] == {
        "recency": 2,
        "k": 1,
        "coverage": 1,
    }
    assert accounting["candidates_by_path"]["coverage"] == 1


def test_dropped_episodes_are_attributed_to_their_path() -> None:
    recency = [episode("n0", 100, size=4_000)]
    k_hits = [episode("k0", 40, size=10)]
    tiers = state(recency, k_hits)
    budget = len(render_stm_payload([], k_hits))

    packed = pack_arm(tiers, arm="B1", budget=budget)
    dropped = dropped_by_path(tiers, packed)

    assert dropped["k"] == []
    assert dropped["recency"] == ["n0"]


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


def test_b0_gate_fails_on_matching_counts_with_different_episodes(
    monkeypatch, tmp_path
) -> None:
    """The surrogate the audit names: the count can match on other episodes."""

    recency = [episode("n0", 100)]
    tiers = {120: state(recency, [])}
    packed = {120: pack_arm(tiers[120], arm="B0", budget=200_000)}
    record = {
        "q11": {
            "fact_count": 6,
            "domain_count": 3,
            "per_domain": {"civil": 4, "art": 0, "monetary": 0, "marine": 2},
            "items": [],
            "serialized_chars": packed[120].serialized_chars,
            "payload_sha256": packed[120].payload_sha256,
            "selected_ids": list(packed[120].selected_ids),
        }
    }
    committed = {
        "fact_count": 6,
        "domain_count": 3,
        "serialized_chars": packed[120].serialized_chars,
        "selected_episode_count": 1,
        "selected_ids": ["a-different-episode"],
        "payload_sha256": packed[120].payload_sha256,
        "items": [],
    }
    path = tmp_path / "a0_baseline.json"
    path.write_text(json.dumps(committed), encoding="utf-8")
    monkeypatch.setattr(
        "src.analysis.ic001_internal_packing.COMMITTED_A0", path
    )

    gate = b0_gate(tiers, packed, record)

    assert gate["status"] == "FAIL"
    assert gate["checks"]["fact_count"] is True
    assert gate["checks"]["episode_identities"] is False


def test_the_authorized_amendment_is_bound_to_every_run() -> None:
    from src.analysis.ic001_internal_packing import (
        AMENDMENT_001,
        _input_paths,
        amendment_authorization,
    )

    authorization = amendment_authorization()
    assert authorization["status"] == "PASS"
    assert authorization["amendment_status"] == "AUTHORIZED"
    assert AMENDMENT_001 in _input_paths()


def test_an_unauthorized_amendment_stops_the_run(monkeypatch, tmp_path) -> None:
    """Reverting the status line must stop IC-001, not change its meaning."""

    from src.analysis import ic001_internal_packing as harness

    revoked = tmp_path / "AMENDMENT_001_no_vector_recomputation.md"
    revoked.write_text(
        harness.AMENDMENT_001.read_text(encoding="utf-8").replace(
            "**Status:** AUTHORIZED",
            "**Status:** PROPOSED - AWAITING PROGRAM AUTHOR AUTHORIZATION",
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(harness, "AMENDMENT_001", revoked)

    authorization = harness.amendment_authorization()
    assert authorization["status"] == "FAIL"
    assert authorization["authorized"] is False

    with pytest.raises(RuntimeError, match="not authorized"):
        harness.run_phase(tmp_path / "runs", "b0")
    assert not (tmp_path / "runs").exists()


def test_mechanism_cannot_reach_the_answer_key() -> None:
    audit = leakage_audit()
    assert audit["status"] == "PASS"
    assert audit["forbidden_imports"] == []
    assert audit["planted_forbidden_path_rejected"] is True
    with pytest.raises(ValueError):
        assert_mechanism_path_allowed("experiments/study_009/q_facts_key.md")


def test_deployed_equivalence_is_not_claimed_for_b1() -> None:
    tiers = state([episode("n0", 100)], [episode("k0", 40)])
    packed = pack_arm(tiers, arm="B1", budget=200_000)
    with pytest.raises(IC001Error):
        assert_b0_matches_deployed_packer(tiers, packed, budget=200_000)


# --------------------------------------------------------------------------
# Paired comparison and the registered decision rule
# --------------------------------------------------------------------------


def arm_record(q11_available, targeted_available) -> dict:
    items = [
        {"domain": "civil", "item": f"item{index}", "available": value}
        for index, value in enumerate(q11_available)
    ]
    targeted = {
        question: {
            "turn": 110 + index,
            "items": [
                {"item": f"{question}_i{position}", "available": value}
                for position, value in enumerate(values)
            ],
            "available_count": sum(1 for value in values if value),
            "item_count": len(values),
        }
        for index, (question, values) in enumerate(targeted_available.items())
    }
    return {
        "q11": {
            "fact_count": sum(1 for value in q11_available if value),
            "domain_count": 1,
            "per_domain": {"civil": sum(1 for v in q11_available if v)},
            "items": items,
        },
        "targeted": targeted,
        "targeted_available_total": sum(
            entry["available_count"] for entry in targeted.values()
        ),
    }


def comparison_for(q11_before, q11_after, targeted_before, targeted_after, monkeypatch):
    monkeypatch.setattr(
        "src.analysis.ic001_internal_packing.TARGETED_QUESTIONS",
        tuple(targeted_before),
    )
    monkeypatch.setattr(
        "src.analysis.ic001_internal_packing.committed_targeted_items",
        lambda: {},
    )
    return paired_comparison(
        arm_record(q11_before, targeted_before),
        arm_record(q11_after, targeted_after),
    )


def test_paired_counts_report_gains_and_losses_separately(monkeypatch) -> None:
    comparison = comparison_for(
        [True, False, False],
        [False, True, True],
        {"Q1": [True, True]},
        {"Q1": [True, True]},
        monkeypatch,
    )
    assert comparison["q11"]["delta"] == 1
    assert comparison["q11"]["gain_count"] == 2
    assert comparison["q11"]["loss_count"] == 1


def test_branch_a_requires_a_rise_with_no_targeted_fall(monkeypatch) -> None:
    comparison = comparison_for(
        [False, False],
        [True, False],
        {"Q1": [True, False]},
        {"Q1": [True, True]},
        monkeypatch,
    )
    assert verdict(comparison)["branch"] == "A"


def test_branch_b_is_a_zero_delta(monkeypatch) -> None:
    comparison = comparison_for(
        [True, False],
        [True, False],
        {"Q1": [True]},
        {"Q1": [True]},
        monkeypatch,
    )
    assert verdict(comparison)["branch"] == "B"


def test_branch_c_is_the_lv_001_trade(monkeypatch) -> None:
    comparison = comparison_for(
        [False, False],
        [True, True],
        {"Q1": [True, True], "Q2": [True]},
        {"Q1": [True, False], "Q2": [True]},
        monkeypatch,
    )
    branch = verdict(comparison)
    assert branch["branch"] == "C"
    assert branch["falling_probes"] == ["Q1"]


def test_branch_d_is_a_fall_on_the_breadth_probe(monkeypatch) -> None:
    comparison = comparison_for(
        [True, True],
        [True, False],
        {"Q1": [True]},
        {"Q1": [True]},
        monkeypatch,
    )
    assert verdict(comparison)["branch"] == "D"


def test_a_per_probe_fall_hidden_by_the_aggregate_still_reads_as_a_fall(
    monkeypatch,
) -> None:
    """Aggregates hide per-probe swings; the rule is applied per probe."""

    comparison = comparison_for(
        [False],
        [True],
        {"Q1": [True, True], "Q2": [False, False]},
        {"Q1": [True, False], "Q2": [True, True]},
        monkeypatch,
    )
    assert comparison["targeted"]["total_delta"] == 1
    assert comparison["targeted"]["falls_any_probe"] is True
    assert comparison["targeted"]["indicators_agree"] is False
    assert verdict(comparison)["branch"] == "C"
