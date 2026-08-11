from __future__ import annotations

from pathlib import Path

import pytest

from src.analysis.ps003_preflight import (
    build_preflight,
    committed_prerequisites,
    guarded_answer_key_load,
    planted_label_ordering_sentinel,
    write_preflight,
)


def test_committed_prerequisites_bind_selected_cell_and_commit_order() -> None:
    result = committed_prerequisites()

    assert result["status"] == "PASS"
    assert all(result["fixed_hashes"].values())
    assert all(result["adjacent_ancestry"])
    assert result["selected_digest"].startswith("70b23e1d")


def test_bad_selected_digest_short_circuits_before_label_reader() -> None:
    prerequisites = committed_prerequisites()
    sentinel = planted_label_ordering_sentinel(prerequisites)

    assert sentinel == {
        "status": "PASS",
        "bad_selected_digest_rejected": True,
        "label_reader_called": False,
    }
    bad = dict(prerequisites, status="FAIL")
    with pytest.raises(RuntimeError, match="before label parse"):
        guarded_answer_key_load(bad, lambda _path: "{}")


def test_full_preflight_answers_pf1_through_pf10() -> None:
    result = build_preflight()

    assert result["status"] == "PASS"
    assert result["check_order"] == [
        "PF1",
        "PF2",
        "PF3",
        "PF4",
        "PF5",
        "PF6",
        "PF7",
        "PF8",
        "PF9",
        "PF10",
    ]
    assert all(check["status"] == "PASS" for check in result["checks"].values())
    assert result["checks"]["PF2"]["executed_probe_count"] == 985
    assert result["checks"]["PF4"]["reachability"]["fact_count"] == 28
    assert not result["checks"]["PF10"]["offline_availability_is_answer_verdict"]


def test_preflight_refuses_overwrite_before_execution(tmp_path: Path) -> None:
    output = tmp_path / "preflight.json"
    output.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError, match="overwrite"):
        write_preflight(output)
