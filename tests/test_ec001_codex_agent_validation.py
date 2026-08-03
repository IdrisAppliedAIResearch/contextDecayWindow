from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_ec001_codex_adjudicator_output import (
    validate_adjudications,
)
from scripts.validate_ec001_codex_calibration import validate_calibration
from scripts.validate_ec001_codex_rater_output import validate_rater_rows
from src.analysis.ec001_tier2 import build_label_prompt

REPO = Path(__file__).resolve().parent.parent
EC001 = REPO / "experiments" / "external" / "longmemeval"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_codex_blind_calibration_is_exact_and_hides_labels() -> None:
    registered = json.loads(
        (EC001 / "runs" / "scoring_001" / "calibration_set.json").read_text(
            encoding="utf-8"
        )
    )
    blind = [
        json.loads(line)
        for line in (
            EC001 / "EC_001_CODEX_AGENT_CALIBRATION_BLIND.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]

    assert [row["calibration_id"] for row in blind] == [
        row["calibration_id"] for row in registered
    ]
    for source, blinded in zip(registered, blind, strict=True):
        assert set(blinded) == {"calibration_id", "label_prompt"}
        assert blinded["label_prompt"] == build_label_prompt(
            source["question_type"],
            source["question"],
            source["reference_answer"],
            source["response"],
            abstention=source["abstention"],
        )


def test_codex_runtime_record_hashes_are_current() -> None:
    runtime = json.loads(
        (EC001 / "EC_001_CODEX_AGENT_RUNTIME_RECORD.json").read_text(
            encoding="utf-8"
        )
    )
    records = list(runtime["locked_inputs"].values()) + runtime["validators"]
    local_raters = [
        row for row in runtime["rater_panel"] if "artifact_sha256" in row
    ]
    records.extend(
        {
            "path": row["artifact"],
            "sha256": row["artifact_sha256"],
        }
        for row in local_raters
    )

    for record in records:
        assert _sha256(REPO / record["path"]) == record["sha256"]


def test_codex_calibration_passes_exact_registered_shape() -> None:
    expected = [
        {"calibration_id": "a", "expected_label": True},
        {"calibration_id": "b", "expected_label": False},
    ]
    observations = {
        "stage": "C1",
        "display_model": "GPT-5.4",
        "calibration": [
            {
                "calibration_id": "a",
                "label": True,
                "label_response": "yes",
            },
            {
                "calibration_id": "b",
                "label": False,
                "label_response": "no",
            },
        ],
    }

    result = validate_calibration(
        observations,
        expected,
        stage="C1",
        display_model="GPT-5.4",
    )

    assert result["status"] == "PASS"
    assert result["failed_calibration_ids"] == []


def test_codex_calibration_records_semantic_failure() -> None:
    expected = [{"calibration_id": "a", "expected_label": False}]
    observations = {
        "stage": "C1",
        "display_model": "GPT-5.4",
        "calibration": [
            {
                "calibration_id": "a",
                "label": True,
                "label_response": "yes",
            }
        ],
    }

    result = validate_calibration(
        observations,
        expected,
        stage="C1",
        display_model="GPT-5.4",
    )

    assert result["status"] == "FAIL"
    assert result["failed_calibration_ids"] == ["a"]


def _rater_row(*, mechanical: bool) -> dict:
    return {
        "anon_id": "masked-1",
        "stage": "C1",
        "display_model": "GPT-5.4",
        "family_id": "codex-gpt54",
        "model_family": "gpt-5.4",
        "model_id": "GPT-5.4 (Codex hosted display selection)",
        "label": False if mechanical else True,
        "label_response": "MECHANICAL_ZERO" if mechanical else "yes",
        "rationale": "Grounded rationale.",
        "rater_called": not mechanical,
        "mechanical_zero": mechanical,
    }


@pytest.mark.parametrize("mechanical", [False, True])
def test_codex_rater_validation_accepts_registered_rows(
    mechanical: bool,
) -> None:
    packets = [{"anon_id": "masked-1", "mechanical_zero": mechanical}]

    result = validate_rater_rows(
        [_rater_row(mechanical=mechanical)],
        packets,
    )

    assert result["question_count"] == 1
    assert result["mechanical_zero_count"] == int(mechanical)


def test_codex_rater_validation_rejects_positive_mechanical_zero() -> None:
    row = _rater_row(mechanical=True)
    row["label"] = True

    with pytest.raises(RuntimeError, match="mechanical zero"):
        validate_rater_rows(
            [row],
            [{"anon_id": "masked-1", "mechanical_zero": True}],
        )


def test_codex_adjudicator_validation_accepts_registered_row() -> None:
    packets = [
        {
            "anon_id": "masked-1",
            "trigger_class": ["H2"],
            "mechanical_zero": False,
        }
    ]
    rows = [
        {
            "anon_id": "masked-1",
            "trigger_class": ["H2"],
            "stage": "C2",
            "display_model": "GPT-5.5",
            "adjudicator_family": "gpt-5.5",
            "adjudicator_model_id": (
                "GPT-5.5 (Codex hosted display selection)"
            ),
            "label": False,
            "label_response": "no",
            "rationale": "Independent rationale.",
        }
    ]

    result = validate_adjudications(rows, packets)

    assert result == {"item_count": 1, "positive_count": 0}


def test_codex_adjudicator_rejects_positive_mechanical_zero() -> None:
    packets = [
        {
            "anon_id": "masked-1",
            "trigger_class": ["H1"],
            "mechanical_zero": True,
        }
    ]
    rows = [
        {
            "anon_id": "masked-1",
            "trigger_class": ["H1"],
            "stage": "C2",
            "display_model": "GPT-5.5",
            "adjudicator_family": "gpt-5.5",
            "adjudicator_model_id": (
                "GPT-5.5 (Codex hosted display selection)"
            ),
            "label": True,
            "label_response": "yes",
            "rationale": "Incorrect positive.",
        }
    ]

    with pytest.raises(RuntimeError, match="Mechanical zero"):
        validate_adjudications(rows, packets)
