"""Unit checks for TC-002's statistic, disposition table, arms and gates.

The disposition table is the part of a pre-registration that decides what a
number means, so it is tested branch by branch rather than exercised once by
whatever the run happens to produce. TC-002 adds one hazard TC-001B did not
have: **its null band depends on the budget**, 7 at 32,000 and 4 at 16,000. A
band silently defaulting to the wrong one would change verdicts without
changing any number, so ``band_for`` and ``verdict`` are tested for refusing to
guess.

The identity that makes ``pack_both`` admissible - one clustering pass serving
both fill orders - is tested on constructed stores, where the answer is known
without running the study.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from analysis import tc002_study as study
from analysis.ec002_k_first_packing import build_k_first_context
from analysis.tc002_exploration import TC002ExplorationError, pack_both
from analysis.tc001b_exploration import DUAL_CONFIG, SHIPPED_CONFIG
from analysis.tc002_study import (
    ALPHA,
    ANCHOR,
    ARMS,
    CONTRASTS,
    NULL_BAND_BY_BUDGET,
    PRIMARY_BUDGET,
    PRIMARY_CONTRAST,
    PRIMARY_ENDPOINT,
    SECONDARY_BUDGET,
    SIGNAL_ALPHA,
    TC002Error,
    all_contrasts,
    assert_registration_agrees,
    band_for,
    ec002_provenance,
    paired,
    run_precondition,
    verdict,
)
from episodic._context import build_context
from episodic._embedding import EMBEDDING_DIMENSION
from episodic._packing import pack_stm_payload

C1 = CONTRASTS[0]
C3 = CONTRASTS[2]


def _row(question: str, k_first: bool, n_first: bool, **extra) -> dict:
    base = {
        "question_id": question,
        "sample_id": "conv-41",
        "category": "4",
        "complete_evaluable": True,
        "evidence_episodes": 1,
        "flat_best_evidence_rank": 3,
        "flat_worst_evidence_rank": 9,
        "fill_order_identical_payload": False,
    }
    for arm, hit in (
        ("flat", False),
        ("n_first", n_first),
        ("k_first", k_first),
        ("dual", False),
        ("dual_ranked", False),
    ):
        base[f"{arm}_complete"] = hit
        base[f"{arm}_any"] = hit
        base[f"{arm}_delivered"] = 110
        base[f"{arm}_chars"] = 31_960
        base[f"{arm}_evidence_delivered"] = int(hit)
        base[f"{arm}_evidence_tiers"] = "k" if hit else ""
        base[f"{arm}_recency"] = 0
        base[f"{arm}_k"] = 70
        base[f"{arm}_coverage"] = 1
    base.update(extra)
    return base


def _rows(gains: int, losses: int, ties: int = 0) -> list[dict]:
    out = [_row(f"g{index}", True, False) for index in range(gains)]
    out += [_row(f"l{index}", False, True) for index in range(losses)]
    out += [_row(f"t{index}", True, True) for index in range(ties)]
    return out


def _pair_rows(
    left: str, right: str, gains: int, losses: int, ties: int = 0
) -> list[dict]:
    """Rows shaped for an arbitrary contrast, not only C1's arms."""

    def make(question: str, left_hit: bool, right_hit: bool) -> dict:
        row = _row(question, False, False)
        for arm, hit in ((left, left_hit), (right, right_hit)):
            row[f"{arm}_complete"] = hit
            row[f"{arm}_any"] = hit
            row[f"{arm}_evidence_delivered"] = int(hit)
        return row

    out = [make(f"g{index}", True, False) for index in range(gains)]
    out += [make(f"l{index}", False, True) for index in range(losses)]
    out += [make(f"t{index}", True, True) for index in range(ties)]
    return out


# --------------------------------------------------------------------------
# The band is per budget, and nothing may guess it
# --------------------------------------------------------------------------


def test_the_registered_bands_are_the_measured_ones() -> None:
    assert NULL_BAND_BY_BUDGET == {32_000: 7, 16_000: 4}
    assert band_for(PRIMARY_BUDGET) == 7
    assert band_for(SECONDARY_BUDGET) == 4


def test_an_unregistered_budget_has_no_band_and_is_refused() -> None:
    """A budget with no measured band is not a budget this study may judge at.

    TC-001 and TC-001B each measured one band and could default to it. TC-002
    measured two and found them different, so defaulting is now a way to be
    silently wrong.
    """
    with pytest.raises(TC002Error):
        band_for(24_000)


def test_verdict_requires_a_band_rather_than_defaulting() -> None:
    statistic = paired(_rows(20, 0), "k_first", "n_first", "any")
    with pytest.raises(TypeError):
        verdict(statistic, C1)  # type: ignore[call-arg]


def test_the_wider_band_can_change_a_disposition() -> None:
    """Six gains, zero losses: it carries signal at 16,000 and nothing at 32,000.

    This is the whole reason the band is registered per budget. The same six
    questions moving the same way are a reportable signal against B = 4 and
    are inside the band against B = 7, and no number in the run changes.
    """
    statistic = paired(_rows(6, 0), "k_first", "n_first", "any")
    assert statistic["net"] == 6
    assert verdict(statistic, C1, band=4)["disposition"] == "D2"
    assert verdict(statistic, C1, band=7)["disposition"] == "D0a"


# --------------------------------------------------------------------------
# The disposition table, branch by branch
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gains,losses,band,expected_disposition,expected_verdict",
    [
        (30, 0, 7, "D1", "K_FIRST_WINS"),
        (0, 30, 7, "D3", "N_FIRST_WINS"),
        (9, 1, 7, "D2", "K_FIRST_WINS_CARRIES_SIGNAL"),
        (1, 9, 7, "D4", "N_FIRST_WINS_CARRIES_SIGNAL"),
        (3, 0, 7, "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"),
        (0, 3, 7, "D0a", "NO_DIFFERENCE_ESTABLISHED_INSIDE_BAND"),
        (12, 4, 7, "D0b", "NO_DIFFERENCE_ESTABLISHED_NOT_SEPARABLE"),
    ],
)
def test_every_branch_of_the_table(
    gains: int,
    losses: int,
    band: int,
    expected_disposition: str,
    expected_verdict: str,
) -> None:
    statistic = paired(_rows(gains, losses, ties=40), "k_first", "n_first", "any")
    outcome = verdict(statistic, C1, band=band)
    assert outcome["disposition"] == expected_disposition
    assert outcome["verdict"] == expected_verdict


def test_the_table_is_exhaustive_over_the_grid() -> None:
    """No (gains, losses) pair may fall through the table."""
    seen = set()
    for gains in range(0, 15):
        for losses in range(0, 15):
            outcome = verdict(
                paired(_rows(gains, losses, ties=5), "k_first", "n_first", "any"),
                C1,
                band=7,
            )
            assert outcome["disposition"] in {"D0a", "D0b", "D1", "D2", "D3", "D4"}
            seen.add(outcome["disposition"])
    assert {"D0a", "D1", "D3"} <= seen


def test_band_is_checked_before_the_p_value() -> None:
    """A unanimous split inside the band is D0a, not a win.

    Five gains and no losses gives p = 0.031, which fails alpha anyway - but
    the table must reach D0a on the band, not on the p-value, or a wider
    population with the same net would slip through.
    """
    statistic = paired(_rows(6, 0, ties=400), "k_first", "n_first", "any")
    assert statistic["p_left_one_sided"] < SIGNAL_ALPHA
    assert verdict(statistic, C1, band=7)["disposition"] == "D0a"


def test_c3s_thin_bar_can_still_fire_at_ten_discordant_pairs() -> None:
    """PF4 registered C3 as reachable and thin; this is the arithmetic.

    Ten discordant pairs, parity forbidding odd nets: 10-0 reaches D1, 9-1
    reaches D2, and 8-2 is inside the band of 7.
    """
    for gains, losses, expected in ((10, 0, "D1"), (9, 1, "D2"), (8, 2, "D0a")):
        statistic = paired(
            _pair_rows("dual", "k_first", gains, losses, ties=800),
            "dual",
            "k_first",
            "any",
        )
        assert statistic["discordant"] == 10
        assert verdict(statistic, C3, band=7)["disposition"] == expected


def test_alphas_are_the_bonferroni_values_for_four_contrasts() -> None:
    assert len(CONTRASTS) == 4
    assert ALPHA == pytest.approx(0.01 / 4)
    assert SIGNAL_ALPHA == pytest.approx(0.10 / 4)


def test_every_contrast_carries_a_bar() -> None:
    """Unlike TC-001B's C3, no TC-002 contrast is registered DESCRIPTIVE."""
    assert study.NO_BAR == frozenset()
    outcomes = all_contrasts(_rows(30, 0, ties=100), "any", band=7)
    for identifier in ("C1", "C2", "C3", "C4"):
        assert outcomes[identifier]["disposition"] != "DESCRIPTIVE"


def test_the_headline_and_endpoint_are_registered() -> None:
    assert PRIMARY_CONTRAST == "C1"
    assert PRIMARY_ENDPOINT == "any"
    assert CONTRASTS[0][:3] == ("C1", "k_first", "n_first")


def test_the_arms_are_the_registered_five() -> None:
    assert ARMS == ("flat", "n_first", "k_first", "dual", "dual_ranked")


# --------------------------------------------------------------------------
# pack_both is the two shipped functions, not a rewrite of them
# --------------------------------------------------------------------------


def _store(count: int) -> list[dict]:
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
                "assistant_message": f"answer number {index} " + "x" * (index % 23),
                "embedding": vector,
            }
        )
    return rows


def _query() -> np.ndarray:
    query = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)
    query[0] = 1.0
    query[3] = 0.4
    return query


@pytest.mark.parametrize("budget", (1_500, 4_000, 40_000))
@pytest.mark.parametrize("config", (SHIPPED_CONFIG, DUAL_CONFIG))
def test_pack_both_reproduces_both_shipped_functions(budget: int, config) -> None:
    records = _store(30)
    both = pack_both(records, _query(), budget, config)
    expected_n, _report = build_context(
        episodes=records, query_embedding=_query(), budget=budget, config=config
    )
    expected_k, _report, _diagnostics = build_k_first_context(
        episodes=records, query_embedding=_query(), budget=budget, config=config
    )
    assert both["n_first"]["payload"] == expected_n
    assert both["k_first"]["payload"] == expected_k


@pytest.mark.parametrize("budget", (1_500, 4_000, 40_000))
def test_k_first_collapses_onto_n_first_with_no_recency_tier(budget: int) -> None:
    """The name-to-behavior check, on a constructed store.

    The registered manipulation is admission order between recency and K.
    Remove the recency tier and it has no subject, so the two paths must agree
    byte for byte. If this ever fails, K-first is doing something the
    registration did not name and TC-002's contrast is not a fill-order
    contrast.
    """
    records = _store(30)
    both = pack_both(records, _query(), budget, DUAL_CONFIG)
    assert both["n_first"]["payload"] == both["k_first"]["payload"]


def test_k_first_never_delivers_fewer_k_episodes() -> None:
    records = _store(40)
    for budget in (1_200, 2_500, 6_000):
        both = pack_both(records, _query(), budget, SHIPPED_CONFIG)
        assert both["k_first"]["counts"]["k"] >= both["n_first"]["counts"]["k"]


def test_the_n_first_pack_is_the_shipped_packer_on_the_shared_state() -> None:
    """pack_both's N-first side is pack_stm_payload, called not reimplemented."""
    from analysis.ec002_k_first_packing import build_candidate_state

    records = _store(30)
    state = build_candidate_state(
        episodes=records,
        query_embedding=_query(),
        budget=4_000,
        config=SHIPPED_CONFIG,
    )
    direct = pack_stm_payload(
        list(state.recent), [*state.k_hits, *state.coverage], 4_000
    )
    both = pack_both(records, _query(), 4_000, SHIPPED_CONFIG)
    assert both["n_first"]["payload"] == direct.payload


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


def test_the_registration_carries_every_constant_this_module_uses() -> None:
    result = assert_registration_agrees()
    assert result["status"] == "PASS"
    assert len(result["pre_registration_sha256"]) == 64


def test_the_anchor_table_matches_the_committed_tc001_summary() -> None:
    """G0's transcribed values are TC-001's, not a paraphrase of them."""
    committed = json.loads(study.TC001_SUMMARY.read_text(encoding="utf-8"))
    blocks = {"16000": committed["primary"], "32000": committed["secondary_budget"]}
    keys = {
        "complete": "primary_complete_evidence",
        "any": "secondary_any_evidence",
    }
    for (budget, endpoint), expected in ANCHOR.items():
        block = blocks[budget][keys[endpoint]]
        assert (
            block["flat_hits"],
            block["tiered_hits"],
            block["gains"],
            block["losses"],
            block["net"],
        ) == expected


def test_ec002_provenance_names_every_file_on_the_k_first_path() -> None:
    result = ec002_provenance()
    assert result["status"] == "PASS"
    assert "src/analysis/ec002_k_first_packing.py" in result["unchanged_since_ec002_run"]
    assert all(result["unchanged_since_ec002_run"].values())


def test_the_run_phase_refuses_to_start_without_a_committed_g0(
    tmp_path: Path,
) -> None:
    with pytest.raises(TC002Error):
        run_precondition(tmp_path)

    gate = tmp_path / "g0"
    gate.mkdir()
    (gate / "g0_reproduction.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )
    # Present but untracked, and outside the repository: still refused.
    with pytest.raises(TC002Error):
        run_precondition(tmp_path)


def test_an_unregistered_phase_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TC002Error):
        study.run_phase(tmp_path, "exploratory")


def test_the_pf4_artifact_carries_no_directional_key() -> None:
    """The Preflight artifact the bars were locked against stays direction-free."""
    from analysis.tc002_reachability import _forbid_direction

    payload = json.loads(study.PF4_ARTIFACT.read_text(encoding="utf-8"))
    _forbid_direction(payload)
    with pytest.raises(TC002ExplorationError):
        _forbid_direction({"budgets": {"32000": {"gains": 1}}})
