from __future__ import annotations

import json

import pytest

from src.analysis.retrieval_bakeoff_tier6_scoring import (
    CALIBRATION_PATH,
    CREDIT_CATALOG,
    blind_calibration_payload,
    derive_score,
    mechanical_evidence,
    validate_calibration_result,
)


def test_q11_requires_fourteen_atomic_items() -> None:
    ids = list(CREDIT_CATALOG["Q11"])
    assert derive_score("Q11", set(ids[:13])) == 0.0
    assert derive_score("Q11", set(ids[:14])) == 1.0


def test_q14_requires_all_domains_named() -> None:
    four_hits = {
        f"q14_{domain}_{suffix}"
        for domain in ("civil", "art", "monetary", "marine")
        for suffix in ("named", "hit")
    }
    assert derive_score("Q14", four_hits) == 1.0

    one_lapse = four_hits - {"q14_art_hit"}
    assert derive_score("Q14", one_lapse) == 0.5

    omitted = one_lapse - {"q14_art_named"}
    assert derive_score("Q14", omitted) == 0.0


def test_q11_mechanical_evidence_finds_registered_items() -> None:
    answer = (
        "Halcyon Crossing: 847 meters, S460ML, 92.4 metric tons per axle, "
        "Dr. Anara Bekova. The Annunciation of Forli by Melozzo da Forli "
        "for Cardinal Giuliano della Rovere, 1483. Federal Reserve, Taylor "
        "Rule, Dr. Priya Mehta, 2.3% and 2%. Vampyroteuthis infernalis, "
        "Dr. Kenji Watanabe, 600-900 meters."
    )
    evidence = mechanical_evidence("Q11", answer)
    assert len(evidence["supported_item_ids"]) == 17


def test_q6_bleed_blocks_clean_credit() -> None:
    clean = (
        "Cardinal Giuliano della Rovere was the patron and later became "
        "Pope Julius II."
    )
    contaminated = clean + " This was related to the Taylor Rule."
    assert mechanical_evidence("Q6", clean)["supported_item_ids"] == [
        "clean_patron_and_pope"
    ]
    assert mechanical_evidence("Q6", contaminated)[
        "supported_item_ids"
    ] == []


def test_calibration_validator_requires_exact_scores(tmp_path) -> None:
    source = json.loads(
        CALIBRATION_PATH.read_text(encoding="utf-8")
    )
    payload = {
        "items": [
            {
                "id": item["id"],
                "primary": item["expected"],
                "strict": item.get(
                    "strict_expected",
                    item["expected"],
                ),
                "rationale": item["reason"],
            }
            for item in source["items"]
        ]
    }
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert validate_calibration_result(path)["status"] == "PASS"

    payload["items"][0]["primary"] = 1.0
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Calibration failed"):
        validate_calibration_result(path)


def test_blind_calibration_packet_withholds_answers() -> None:
    packet = blind_calibration_payload()
    assert packet["metadata"]["expected_scores_withheld"] is True
    for item in packet["items"]:
        assert set(item) == {
            "id",
            "criterion",
            "scoring_reference",
            "response",
        }
        assert "expected" not in item
