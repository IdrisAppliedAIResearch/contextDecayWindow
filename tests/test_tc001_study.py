"""Unit checks for TC-001's statistic, its disposition table, and its gate.

The disposition table is the part of a pre-registration that decides what
a number means, so it is tested branch by branch rather than exercised
once by whatever the run happens to produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analysis import tc001_study as study
from analysis.tc001_study import (
    NULL_BAND,
    TC001Error,
    assert_registration_agrees,
    discordant_rows,
    one_sided_sign_p,
    paired,
    run_precondition,
    verdict,
)


def _row(question: str, flat: bool, tiered: bool, **extra) -> dict:
    base = {
        "question_id": question,
        "sample_id": "conv-41",
        "category": "4",
        "flat_complete": flat,
        "tiered_complete": tiered,
        "flat_any": flat,
        "tiered_any": tiered,
        "evidence_episodes": 1,
        "tiered_evidence_tiers": "k" if tiered else "",
        "tiered_evidence_delivered": int(tiered),
        "flat_evidence_delivered": int(flat),
        "flat_best_evidence_rank": 3,
        "flat_worst_evidence_rank": 9,
        "tiered_recency": 32,
        "tiered_k": 20,
        "tiered_coverage": 0,
    }
    base.update(extra)
    return base


def test_one_sided_sign_test_matches_the_pf4_probe() -> None:
    # The reachability probe reports 0.5 ** d as the best p reachable at d
    # discordant pairs. The two have to agree or one of them is wrong.
    assert one_sided_sign_p(451, 451) == pytest.approx(0.5**451)
    assert one_sided_sign_p(0, 0) == 1.0
    assert one_sided_sign_p(1, 2) == 0.75
    assert one_sided_sign_p(2, 2) == 0.25


def test_paired_counts_gains_losses_and_ties() -> None:
    rows = [
        _row("a", flat=False, tiered=True),
        _row("b", flat=True, tiered=False),
        _row("c", flat=True, tiered=True),
        _row("d", flat=False, tiered=False),
        _row("e", flat=False, tiered=True),
    ]
    result = paired(rows, "complete")
    assert (result["gains"], result["losses"], result["ties"]) == (2, 1, 2)
    assert result["net"] == 1
    assert result["discordant"] == 3
    assert result["flat_hits"] == 2
    assert result["tiered_hits"] == 3


@pytest.mark.parametrize(
    "net, p_tiered, p_flat, expected",
    [
        (0, 0.5, 0.5, "D0a"),
        (NULL_BAND - 1, 0.30, 0.70, "D0a"),
        (-(NULL_BAND - 1), 0.70, 0.30, "D0a"),
        (NULL_BAND, 0.004, 0.996, "D1"),
        (NULL_BAND, 0.050, 0.950, "D2"),
        (-NULL_BAND, 0.996, 0.004, "D3"),
        (-NULL_BAND, 0.950, 0.050, "D4"),
        (40, 0.400, 0.600, "D0b"),
        (-40, 0.600, 0.400, "D0b"),
    ],
)
def test_every_disposition_branch_is_reachable(
    net: int, p_tiered: float, p_flat: float, expected: str
) -> None:
    statistic = {
        "net": net,
        "p_tiered_one_sided": p_tiered,
        "p_flat_one_sided": p_flat,
    }
    assert verdict(statistic)["disposition"] == expected


def test_a_margin_inside_the_band_is_not_a_win_for_either_arm() -> None:
    # The registration says explicitly that simplicity is not entitled to
    # a free pass: a small negative net is no difference, not a flat win.
    statistic = {
        "net": -(NULL_BAND - 1),
        "p_tiered_one_sided": 1.0,
        "p_flat_one_sided": 0.0001,
    }
    result = verdict(statistic)
    assert result["disposition"] == "D0a"
    assert "NO_DIFFERENCE" in result["verdict"]


def test_discordant_rows_label_direction_and_drop_ties() -> None:
    rows = [
        _row("gain", flat=False, tiered=True),
        _row("loss", flat=True, tiered=False),
        _row("tie", flat=True, tiered=True),
    ]
    out = discordant_rows(rows, "complete")
    assert [row["direction"] for row in out] == ["gain", "loss"]
    assert {row["question_id"] for row in out} == {"gain", "loss"}


def test_registered_constants_must_appear_in_the_locked_document() -> None:
    assert assert_registration_agrees()["status"] == "PASS"


def test_a_constant_that_left_the_document_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    decoy = tmp_path / "TC_001_PRE_REGISTRATION.md"
    decoy.write_text("nothing registered here", encoding="utf-8")
    monkeypatch.setattr(study, "PRE_REGISTRATION", decoy)
    with pytest.raises(TC001Error):
        assert_registration_agrees()


def test_the_run_phase_refuses_to_start_without_a_committed_gate(
    tmp_path: Path,
) -> None:
    # PF3: Study 011 ran its determinism check after every arm was scored.
    # A gate that runs afterward is not a gate.
    with pytest.raises(TC001Error):
        run_precondition(tmp_path)

    gate = tmp_path / "g0" / "g0_reproduction.json"
    gate.parent.mkdir(parents=True)
    gate.write_text('{"status": "PASS"}', encoding="utf-8")
    with pytest.raises(TC001Error):
        # Present but untracked by git, which is the same as absent here.
        run_precondition(tmp_path)


def test_the_model_call_guard_counts_and_refuses() -> None:
    import sys
    import types

    module = types.ModuleType("src.embeddings.provider")
    module._get_model = lambda: "a model"
    sys.modules["src.embeddings.provider"] = module
    try:
        with study.ModelCallGuard() as guard:
            assert "src.embeddings.provider._get_model" in guard.armed
            with pytest.raises(TC001Error):
                sys.modules["src.embeddings.provider"]._get_model()
            audit = guard.audit()
        assert audit["status"] == "FAIL"
        assert audit["model_calls"] == 1
        # Restored on exit, so a guard cannot leak into the next test.
        assert sys.modules["src.embeddings.provider"]._get_model() == "a model"
    finally:
        del sys.modules["src.embeddings.provider"]
