"""Unit checks for TC-001B's statistic, disposition table, arms and gates.

The disposition table is the part of a pre-registration that decides what a
number means, so it is tested branch by branch rather than exercised once by
whatever the run happens to produce. The identity gate that makes
``A_DUAL_RANKED`` admissible is tested on constructed stores, where the answer
is known without running the study.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from analysis import tc001b_study as study
from analysis.tc001b_exploration import (
    DUAL_CONFIG,
    SHIPPED_CONFIG,
    TC001BExplorationError,
    compose_context,
)
from analysis.tc001b_study import (
    ALPHA,
    CONTRASTS,
    NULL_BAND,
    SIGNAL_ALPHA,
    TC001BError,
    all_contrasts,
    assert_registration_agrees,
    paired,
    run_precondition,
    verdict,
)
from episodic._config import EpisodicConfig
from episodic._embedding import EMBEDDING_DIMENSION
from episodic._context import build_context

C1 = CONTRASTS[0]


def _row(question: str, dual: bool, flat: bool, **extra) -> dict:
    base = {
        "question_id": question,
        "sample_id": "conv-41",
        "category": "4",
        "complete_evaluable": True,
        "evidence_episodes": 1,
        "flat_best_evidence_rank": 3,
        "flat_worst_evidence_rank": 9,
    }
    for arm, hit in (
        ("flat", flat),
        ("tiered", False),
        ("dual", dual),
        ("dual_ranked", dual),
    ):
        base[f"{arm}_complete"] = hit
        base[f"{arm}_any"] = hit
        base[f"{arm}_delivered"] = 50
        base[f"{arm}_chars"] = 15_900
        base[f"{arm}_evidence_delivered"] = int(hit)
        base[f"{arm}_evidence_tiers"] = "k" if hit else ""
    base.update(extra)
    return base


# --------------------------------------------------------------------------
# The statistic
# --------------------------------------------------------------------------


def test_paired_counts_gains_losses_and_ties() -> None:
    rows = [
        _row("a", dual=True, flat=False),
        _row("b", dual=False, flat=True),
        _row("c", dual=True, flat=True),
        _row("d", dual=False, flat=False),
    ]
    statistic = paired(rows, "dual", "flat", "complete")
    assert statistic["gains"] == 1
    assert statistic["losses"] == 1
    assert statistic["ties"] == 2
    assert statistic["discordant"] == 2
    assert statistic["net"] == 0
    assert statistic["left_hits"] == 2
    assert statistic["right_hits"] == 2


def test_paired_is_antisymmetric_in_its_arms() -> None:
    rows = [_row(str(index), dual=index % 3 == 0, flat=index % 2 == 0) for index in range(30)]
    forward = paired(rows, "dual", "flat", "complete")
    backward = paired(rows, "flat", "dual", "complete")
    assert forward["gains"] == backward["losses"]
    assert forward["net"] == -backward["net"]
    assert forward["p_left_one_sided"] == backward["p_right_one_sided"]


# --------------------------------------------------------------------------
# The disposition table, branch by branch
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gains,losses,expected_disposition,expected_verdict",
    [
        (40, 0, "D1", "DUAL_WINS"),
        (0, 40, "D3", "FLAT_WINS"),
        (2, 0, "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"),
        (0, 2, "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"),
        (12, 4, "D0b", "NO_DIFFERENCE_ESTABLISHED_NOT_SEPARABLE"),
        (4, 12, "D0b", "NO_DIFFERENCE_ESTABLISHED_NOT_SEPARABLE"),
    ],
)
def test_every_disposition_branch(
    gains: int, losses: int, expected_disposition: str, expected_verdict: str
) -> None:
    rows = [_row(f"g{i}", dual=True, flat=False) for i in range(gains)]
    rows += [_row(f"l{i}", dual=False, flat=True) for i in range(losses)]
    rows += [_row(f"t{i}", dual=True, flat=True) for i in range(20)]
    outcome = verdict(paired(rows, "dual", "flat", "complete"), C1)
    assert outcome["disposition"] == expected_disposition
    assert outcome["verdict"] == expected_verdict


def test_signal_tier_fires_between_the_two_alphas() -> None:
    # 11 of 11 discordant pairs one way: p = 0.5**11 = 0.000488, below
    # ALPHA. 9 of 9 gives 0.00195, still below. 8 of 8 gives 0.0039, which
    # sits between ALPHA and SIGNAL_ALPHA - the registered lower tier.
    rows = [_row(f"g{i}", dual=True, flat=False) for i in range(8)]
    rows += [_row(f"t{i}", dual=True, flat=True) for i in range(20)]
    outcome = verdict(paired(rows, "dual", "flat", "complete"), C1)
    assert ALPHA < outcome["statistic"]["p_left_one_sided"] <= SIGNAL_ALPHA
    assert outcome["disposition"] == "D2"
    assert outcome["verdict"] == "DUAL_WINS_CARRIES_SIGNAL"


def test_band_is_checked_before_the_p_value() -> None:
    # 3 gains, 0 losses: p = 0.125, and |net| = 3 < B = 4. The band branch
    # must win, or a study could report a win inside its own null band.
    rows = [_row(f"g{i}", dual=True, flat=False) for i in range(3)]
    outcome = verdict(paired(rows, "dual", "flat", "complete"), C1)
    assert NULL_BAND == 4
    assert outcome["disposition"] == "D0a"


def test_bonferroni_alphas_are_the_family_adjusted_ones() -> None:
    assert ALPHA == pytest.approx(0.01 / 4)
    assert SIGNAL_ALPHA == pytest.approx(0.10 / 4)


def test_c3_carries_no_bar_and_no_disposition_can_be_read_into_it() -> None:
    # PF4 found C3 unreachable before the lock. Even a lopsided split must
    # come back DESCRIPTIVE: applying the table to a bar that was refused
    # would be reading a verdict out of a contrast that has none.
    c3 = next(contrast for contrast in CONTRASTS if contrast[0] == "C3")
    rows = [_row(f"g{i}", dual=True, flat=False) for i in range(40)]
    rows += [_row(f"t{i}", dual=True, flat=True) for i in range(20)]
    outcome = verdict(paired(rows, "dual_ranked", "flat", "complete"), c3)
    assert outcome["disposition"] == "DESCRIPTIVE"
    assert outcome["verdict"] == "NO_BAR_REGISTERED"
    # The numbers are still reported - descriptive is not silent.
    assert outcome["statistic"]["gains"] == 40
    assert outcome["statistic"]["net"] == 40
    assert "D1" not in json.dumps(outcome)


def test_the_other_three_contrasts_still_carry_bars() -> None:
    for contrast in CONTRASTS:
        rows = [_row(f"g{i}", dual=True, flat=False) for i in range(40)]
        rows += [_row(f"t{i}", dual=True, flat=True) for i in range(20)]
        outcome = verdict(paired(rows, contrast[1], contrast[2], "complete"), contrast)
        if contrast[0] == "C3":
            continue
        assert outcome["disposition"] in {"D0a", "D0b", "D1", "D2", "D3", "D4"}


def test_contrast_names_follow_their_registered_arms() -> None:
    rows = [_row(f"l{i}", dual=False, flat=True) for i in range(40)]
    rows += [_row(f"t{i}", dual=True, flat=True) for i in range(20)]
    outcomes = all_contrasts(rows, "complete")
    assert set(outcomes) == {"C1", "C2", "C3", "C4"}
    assert outcomes["C1"]["left"] == "dual"
    assert outcomes["C1"]["right"] == "flat"
    assert outcomes["C3"]["left"] == "dual_ranked"
    assert outcomes["C2"]["right"] == "tiered"


# --------------------------------------------------------------------------
# The arms
# --------------------------------------------------------------------------


def _store(count: int) -> list[dict]:
    """A synthetic store in the carried embedder's dimension.

    The vectors are sparse and deliberately collide across episodes, so
    the K threshold fires on some and not others and the cluster
    assignment has something to separate.
    """
    rows = []
    for index in range(count):
        vector = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
        vector[index % 8] = 1.0
        vector[(index * 3) % 8] += 0.5
        rows.append(
            {
                "id": f"e{index:03d}",
                "turn_number": index + 1,
                "user_message": f"question about topic {index % 5}",
                "assistant_message": f"answer number {index} " + "x" * (index % 17),
                "embedding": vector,
            }
        )
    return rows


def test_compose_context_is_build_context_under_store_order() -> None:
    records = _store(60)
    query = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    query[1] = 1.0
    for config in (SHIPPED_CONFIG, DUAL_CONFIG, EpisodicConfig(recency_window_n=5)):
        for budget in (2_000, 8_000, 40_000):
            shipped, _report = build_context(
                episodes=records,
                query_embedding=query,
                budget=budget,
                config=config,
            )
            local, _ids, _counts = compose_context(
                records, query, budget, config, k_order="store"
            )
            assert local == shipped


def test_dual_config_delivers_no_recency_episode() -> None:
    records = _store(60)
    query = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    query[1] = 1.0
    _payload, _ids, counts = compose_context(
        records, query, 8_000, DUAL_CONFIG, k_order="store"
    )
    assert counts["recency"] == 0
    assert DUAL_CONFIG.recency_window_n == 0


def test_ranked_k_order_changes_the_offer_not_the_membership() -> None:
    records = _store(60)
    query = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    query[1] = 1.0
    # A budget large enough for every K hit: the delivered sets must match,
    # because reordering a list that fits entirely cannot change its members.
    _payload, store_ids, _counts = compose_context(
        records, query, 200_000, DUAL_CONFIG, k_order="store"
    )
    _payload, ranked_ids, _counts = compose_context(
        records, query, 200_000, DUAL_CONFIG, k_order="relevance"
    )
    assert set(store_ids) == set(ranked_ids)


def test_unregistered_k_order_is_refused() -> None:
    with pytest.raises(TC001BExplorationError):
        compose_context(_store(4), np.zeros(EMBEDDING_DIMENSION, dtype=np.float32), 8_000,
                        DUAL_CONFIG, k_order="whatever")


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


def test_registration_carries_every_constant() -> None:
    outcome = assert_registration_agrees()
    assert outcome["status"] == "PASS"
    assert outcome["pre_registration"].endswith("TC_001B_PRE_REGISTRATION.md")
    assert outcome["amendment"].endswith("AMENDMENT_001_dual_arm_escalation.md")


def test_registration_gate_rejects_a_document_with_placeholders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = tmp_path / "draft.md"
    text = study.PRE_REGISTRATION.read_text(encoding="utf-8")
    draft.write_text(text + "\n\nPENDING-PART1-BAND\n", encoding="utf-8")
    monkeypatch.setattr(study, "PRE_REGISTRATION", draft)
    with pytest.raises(TC001BError, match="PENDING"):
        assert_registration_agrees()


def test_registration_gate_rejects_a_missing_constant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = tmp_path / "draft.md"
    text = study.PRE_REGISTRATION.read_text(encoding="utf-8")
    draft.write_text(text.replace("`p₊ ≤ 0.0025`", "`p ≤ something`"), encoding="utf-8")
    monkeypatch.setattr(study, "PRE_REGISTRATION", draft)
    with pytest.raises(TC001BError, match="alpha"):
        assert_registration_agrees()


def test_run_precondition_refuses_an_absent_gate(tmp_path: Path) -> None:
    with pytest.raises(TC001BError, match="has not run"):
        run_precondition(tmp_path)


def test_run_precondition_refuses_an_uncommitted_gate(tmp_path: Path) -> None:
    gate = tmp_path / "g0"
    gate.mkdir()
    (gate / "g0_reproduction.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    with pytest.raises(TC001BError, match="not committed"):
        run_precondition(tmp_path)


def test_unregistered_phase_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TC001BError, match="Unregistered phase"):
        study.run_phase(tmp_path, "exploratory")


def test_anchor_table_matches_the_committed_tc001_summary() -> None:
    committed = json.loads(study.TC001_SUMMARY.read_text(encoding="utf-8"))
    blocks = {
        "16000": committed["primary"],
        "32000": committed["secondary_budget"],
    }
    keys = {
        "complete": "primary_complete_evidence",
        "any": "secondary_any_evidence",
    }
    for (budget, endpoint), expected in study.ANCHOR.items():
        block = blocks[budget][keys[endpoint]]
        assert (
            block["flat_hits"],
            block["tiered_hits"],
            block["gains"],
            block["losses"],
            block["net"],
        ) == expected
