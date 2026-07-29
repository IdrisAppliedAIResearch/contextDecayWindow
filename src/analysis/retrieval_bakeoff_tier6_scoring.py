from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Iterable

from src.analysis.scoring_integrity import inspect_completeness, validate_score


REPO_ROOT = Path(__file__).resolve().parents[2]
SURVEY_ROOT = (
    REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff"
)
TIER6_ROOT = SURVEY_ROOT / "tier6"
RUN_ID = os.environ.get("CDW_TIER6_SCORING_RUN_ID", "tier6_live_121")
RUN_ROOT = TIER6_ROOT / "runs"
RUN_DIR = RUN_ROOT / RUN_ID / "context_matched_stm"
LAUNCH_MANIFEST = RUN_ROOT / f"{RUN_ID}_launch_manifest.json"
SCORING_SURFACE = RUN_DIR / "scoring_surface.json"
MECHANISM_SEAL = RUN_DIR / "mechanism_seal.json"
EVALUATION_ROOT = TIER6_ROOT / os.environ.get(
    "CDW_TIER6_EVALUATION_DIR", "evaluation"
)
PREFLIGHT_PATH = TIER6_ROOT / os.environ.get(
    "CDW_TIER6_PREFLIGHT_FILE", "scoring_preflight.json"
)

RUBRIC_PATH = REPO_ROOT / "experiments" / "study_002" / "rubric_filled.md"
Q14_PATH = REPO_ROOT / "experiments" / "study_004" / "q14_criteria.md"
PLANT_KEY_PATH = (
    REPO_ROOT / "experiments" / "study_009" / "q_facts_key.md"
)
SCRIPT_PATH = REPO_ROOT / "experiments" / "study_005" / "script.json"
AUDIT_ROOT = REPO_ROOT / "experiments" / "audits" / "scoring_integrity"
PROTOCOL_PATH = AUDIT_ROOT / "PROTOCOL_scoring_integrity.md"
CALIBRATION_PATH = AUDIT_ROOT / "calibration_set.json"
GUIDANCE_PATH = AUDIT_ROOT / "q11_q14_scoring_guidance.md"
AMENDMENT_PATH = (
    SURVEY_ROOT
    / "amendments"
    / "AMENDMENT_009_tier6_new_arm_triggers.md"
)

QUESTION_ORDER = tuple(f"Q{number}" for number in range(1, 15))
TURN_BY_QUESTION = {
    "Q1": (112,),
    "Q2": (113,),
    "Q3": (114,),
    "Q4": (115,),
    "Q5": (116,),
    "Q6": (117,),
    "Q7": (118,),
    "Q8": (119,),
    "Q9": (117,),
    "Q10": (118,),
    "Q11": (120,),
    "Q12": (114,),
    "Q13": tuple(range(112, 121)),
    "Q14": (121,),
}
ALLOWED_SCORES = {
    "Q1": (0.0, 0.5, 1.0),
    "Q2": (0.0, 0.5, 1.0),
    "Q3": (0.0, 0.5, 1.0),
    "Q4": (0.0, 0.5, 1.0),
    "Q5": (0.0, 0.5, 1.0),
    "Q6": (0.0, 1.0),
    "Q7": (0.0, 0.5, 1.0),
    "Q8": (0.0, 0.5, 1.0),
    "Q9": (0.0, 1.0),
    "Q10": (0.0, 1.0),
    "Q11": (0.0, 1.0),
    "Q12": (0.0, 1.0),
    "Q13": (0.0, 1.0),
    "Q14": (0.0, 0.5, 1.0),
}

CRITERIA = {
    "Q1": (
        "1.0 for both 847 meters and S460ML; 0.5 for exactly one; "
        "otherwise 0."
    ),
    "Q2": (
        "1.0 for both Dr. Anara Bekova and 92.4 metric tons per axle; "
        "0.5 for exactly one; otherwise 0."
    ),
    "Q3": (
        "1.0 for both rules: numbered lists for technical specifications or "
        "multiple items, and a parenthesized Low/Medium/High risk "
        "classification on structural or engineering recommendations; "
        "0.5 for exactly one; otherwise 0."
    ),
    "Q4": (
        "1.0 for The Annunciation of Forli, Melozzo da Forli, Cardinal "
        "Giuliano della Rovere, and 1483; 0.5 for two or three; otherwise 0."
    ),
    "Q5": (
        "1.0 for both lead white ground and ultramarine glaze; 0.5 for "
        "exactly one; otherwise 0."
    ),
    "Q6": (
        "1.0 only for clean Renaissance retrieval identifying Cardinal "
        "Giuliano della Rovere as patron of the painting and later Pope "
        "Julius II, with no monetary-policy or marine-biology contamination; "
        "otherwise 0."
    ),
    "Q7": (
        "1.0 for Vampyroteuthis infernalis, Dr. Kenji Watanabe, the "
        "600-900 meter depth range, and marine snow particle aggregation; "
        "0.5 for two or three; otherwise 0."
    ),
    "Q8": (
        "1.0 for photophores along the mantle margin; 0.5 for exactly the "
        "organ or location; otherwise 0."
    ),
    "Q9": (
        "1.0 only if the turn-117 Renaissance answer is clean and contains "
        "no Taylor Rule, Dr. Priya Mehta, inflation-threshold, "
        "Vampyroteuthis, or Dr. Kenji Watanabe bleed; otherwise 0."
    ),
    "Q10": (
        "1.0 only if Dr. Kenji Watanabe is correctly attributed to "
        "Vampyroteuthis infernalis without researcher conflation; otherwise "
        "0."
    ),
    "Q11": (
        "Binary: 1.0 for at least 14 of the 17 listed atomic items, correctly "
        "attributed, with no significant cross-attribution; otherwise 0. "
        "There is no 0.5 score. Atomic items: 847, S460ML, 92.4 metric tons "
        "per axle, 1483, 600-900 meters, 2.3%, 2%, Halcyon Crossing, "
        "Dr. Anara Bekova, The Annunciation of Forli, Melozzo da Forli, "
        "Cardinal Giuliano della Rovere, Federal Reserve, Taylor Rule, "
        "Dr. Priya Mehta, Vampyroteuthis infernalis, and "
        "Dr. Kenji Watanabe."
    ),
    "Q12": (
        "1.0 only if both behavioral rules are stated correctly; otherwise 0."
    ),
    "Q13": (
        "1.0 if applicable behavioral rules are honored in at least five of "
        "turns 112-120; otherwise 0. The engineering-risk rule is N/A where "
        "no engineering recommendation is requested."
    ),
    "Q14": (
        "A domain hit requires naming the domain and giving at least one "
        "correct planted specific. 1.0 for hits in civil engineering, "
        "Renaissance art, monetary policy, and marine biology. 0.5 if all "
        "four are named and exactly one lacks or has a wrong specific. 0.0 "
        "if any domain is omitted, two or more lack specifics, or the answer "
        "denies that a domain was discussed."
    ),
}

CREDIT_CATALOG = {
    "Q1": {
        "civil_span_847": "847-meter main span",
        "civil_steel_s460ml": "S460ML steel grade",
    },
    "Q2": {
        "civil_engineer_bekova": "Dr. Anara Bekova",
        "civil_load_92_4": "92.4 metric tons per axle",
    },
    "Q3": {
        "rule_numbered_lists": "numbered-list formatting rule",
        "rule_risk_classification": "engineering risk-classification rule",
    },
    "Q4": {
        "art_title": "The Annunciation of Forli",
        "art_artist": "Melozzo da Forli",
        "art_patron": "Cardinal Giuliano della Rovere",
        "art_year_1483": "completion year 1483",
    },
    "Q5": {
        "art_ground_lead_white": "lead white ground",
        "art_glaze_ultramarine": "ultramarine glaze",
    },
    "Q6": {
        "clean_patron_and_pope": (
            "clean patron plus later Pope Julius II identification"
        ),
    },
    "Q7": {
        "marine_species": "Vampyroteuthis infernalis",
        "marine_researcher": "Dr. Kenji Watanabe",
        "marine_depth_600_900": "600-900 meter depth range",
        "marine_feeding": "marine snow particle aggregation",
    },
    "Q8": {
        "marine_photophores": "photophores",
        "marine_mantle_margin": "mantle-margin location",
    },
    "Q9": {
        "clean_renaissance_retrieval": (
            "Renaissance answer without monetary or marine bleed"
        ),
    },
    "Q10": {
        "correct_watanabe_attribution": (
            "Dr. Kenji Watanabe correctly attributed to Vampyroteuthis"
        ),
    },
    "Q11": {
        "q11_847": "847",
        "q11_s460ml": "S460ML",
        "q11_92_4": "92.4 metric tons per axle",
        "q11_1483": "1483",
        "q11_600_900": "600-900 meters",
        "q11_2_3": "2.3%",
        "q11_2": "2%",
        "q11_halcyon": "Halcyon Crossing",
        "q11_bekova": "Dr. Anara Bekova",
        "q11_annunciation": "The Annunciation of Forli",
        "q11_melozzo": "Melozzo da Forli",
        "q11_rovere": "Cardinal Giuliano della Rovere",
        "q11_federal_reserve": "Federal Reserve",
        "q11_taylor_rule": "Taylor Rule",
        "q11_priya": "Dr. Priya Mehta",
        "q11_vampyroteuthis": "Vampyroteuthis infernalis",
        "q11_watanabe": "Dr. Kenji Watanabe",
    },
    "Q12": {
        "rule_numbered_lists": "numbered-list formatting rule",
        "rule_risk_classification": "engineering risk-classification rule",
    },
    "Q13": {
        "late_turn_rule_compliance": (
            "applicable rules honored in at least five of nine turns"
        ),
    },
    "Q14": {
        "q14_civil_named": "civil engineering named",
        "q14_civil_hit": "civil engineering planted-specific hit",
        "q14_art_named": "Renaissance art named",
        "q14_art_hit": "Renaissance art planted-specific hit",
        "q14_monetary_named": "monetary policy named",
        "q14_monetary_hit": "monetary policy planted-specific hit",
        "q14_marine_named": "marine biology named",
        "q14_marine_hit": "marine biology planted-specific hit",
    },
}

ALIASES = {
    "civil_span_847": (("847",),),
    "civil_steel_s460ml": (("s460ml",),),
    "civil_engineer_bekova": (("anara", "bekova"),),
    "civil_load_92_4": (("92.4",),),
    "rule_numbered_lists": (
        ("numbered", "list"),
        ("numbered", "format"),
    ),
    "rule_risk_classification": (
        ("risk", "low", "medium", "high"),
        ("risk classification",),
    ),
    "art_title": (("annunciation", "forl"),),
    "art_artist": (("melozzo", "forl"),),
    "art_patron": (("cardinal", "giuliano", "rovere"),),
    "art_year_1483": (("1483",),),
    "art_ground_lead_white": (("lead white", "ground"),),
    "art_glaze_ultramarine": (("ultramarine", "glaze"),),
    "marine_species": (("vampyroteuthis", "infernalis"),),
    "marine_researcher": (("kenji", "watanabe"),),
    "marine_depth_600_900": (("600", "900"),),
    "marine_feeding": (("marine snow",),),
    "marine_photophores": (("photophore",),),
    "marine_mantle_margin": (("mantle", "margin"),),
    "q11_847": (("847",),),
    "q11_s460ml": (("s460ml",),),
    "q11_92_4": (("92.4",),),
    "q11_1483": (("1483",),),
    "q11_600_900": (("600", "900"),),
    "q11_2_3": (("2.3",),),
    "q11_2": (("2%",), ("2 percent",)),
    "q11_halcyon": (("halcyon crossing",),),
    "q11_bekova": (("anara", "bekova"),),
    "q11_annunciation": (("annunciation", "forl"),),
    "q11_melozzo": (("melozzo", "forl"),),
    "q11_rovere": (("cardinal", "giuliano", "rovere"),),
    "q11_federal_reserve": (("federal reserve",),),
    "q11_taylor_rule": (("taylor rule",),),
    "q11_priya": (("priya", "mehta"),),
    "q11_vampyroteuthis": (("vampyroteuthis", "infernalis"),),
    "q11_watanabe": (("kenji", "watanabe"),),
}

PLANTS = (
    ("rule_numbered_lists", 1, ("numbered", "list")),
    ("rule_risk_classification", 1, ("risk", "low", "medium", "high")),
    ("civil_project", 3, ("halcyon crossing",)),
    ("civil_span", 3, ("847",)),
    ("civil_engineer", 3, ("anara", "bekova")),
    ("civil_steel", 4, ("s460ml",)),
    ("civil_load", 4, ("92.4",)),
    ("art_title", 55, ("annunciation", "forl")),
    ("art_artist", 55, ("melozzo", "forl")),
    ("art_patron", 55, ("cardinal", "giuliano", "rovere")),
    ("art_year", 55, ("1483",)),
    ("art_ground", 56, ("lead white", "ground")),
    ("art_glaze", 56, ("ultramarine", "glaze")),
    ("art_pope", 60, ("pope julius ii",)),
    ("monetary_taylor", 61, ("taylor rule",)),
    ("monetary_fed", 62, ("federal reserve", "dual mandate")),
    ("monetary_priya", 65, ("priya", "mehta")),
    ("monetary_reverse_repo", 65, ("reverse repurchase",)),
    ("monetary_2_3", 65, ("2.3",)),
    ("monetary_2", 65, ("2%",)),
    ("marine_species", 100, ("vampyroteuthis", "infernalis")),
    ("marine_researcher", 100, ("kenji", "watanabe")),
    ("marine_depth", 100, ("600", "900")),
    ("marine_photophores", 101, ("photophore",)),
    ("marine_mantle_margin", 101, ("mantle", "margin")),
    ("marine_feeding", 102, ("marine snow",)),
)

H5_SEED = "retrieval-bakeoff-t6-h5-2026-07-29-v1"
PASS_SEED = "retrieval-bakeoff-t6-pass-order-2026-07-29-v1"
CALIBRATION_REFERENCES = {
    "cal_no_answer": "The two required facts are Alpha and 42.",
    "cal_truncated": (
        "The four domain specifics are Civil Alpha 10, Art Beta 20, "
        "Monetary Gamma 30, and Marine Delta 40."
    ),
    "cal_hedged": "The exact correct material is Material X.",
    "cal_q11_partial": (
        "The response itself states the correctly attributed atomic-item "
        "count; apply the 80% threshold to a 17-item denominator."
    ),
    "cal_q14_one_lapse": (
        "The four domain specifics are Civil Alpha 10, Art Beta 20, "
        "Monetary Gamma 30, and Marine Delta 40."
    ),
    "cal_complete": "The two required facts are Alpha and 42.",
    "cal_wrong": "The two required facts are Alpha and 42.",
}


def write_preflight() -> dict:
    if PREFLIGHT_PATH.exists():
        raise RuntimeError(f"Refusing to overwrite {PREFLIGHT_PATH}")
    script = json.loads(SCRIPT_PATH.read_text(encoding="utf-8"))
    turns = {int(row["turn"]): str(row["user"]) for row in script["turns"]}
    plant_rows = []
    for plant_id, source_turn, terms in PLANTS:
        source = turns[source_turn]
        normalized = normalize(source)
        present = all(normalize(term) in normalized for term in terms)
        plant_rows.append(
            {
                "plant_id": plant_id,
                "source_turn": source_turn,
                "strictly_before_first_probe": source_turn < 112,
                "terms_present": present,
                "terms": list(terms),
            }
        )
    checks = {
        "all_required_plants_present": all(
            row["terms_present"] for row in plant_rows
        ),
        "all_required_plants_precede_probes": all(
            row["strictly_before_first_probe"] for row in plant_rows
        ),
        "script_has_registered_probe_turns": (
            script.get("rubric_turns") == list(range(112, 122))
        ),
        "question_spec_complete": (
            set(CRITERIA)
            == set(CREDIT_CATALOG)
            == set(ALLOWED_SCORES)
            == set(QUESTION_ORDER)
        ),
        "amendment_present": AMENDMENT_PATH.is_file(),
    }
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "run_id": RUN_ID,
        "checks": checks,
        "plant_count": len(plant_rows),
        "plants": plant_rows,
        "source_sha256": {
            _relative(path): sha256(path)
            for path in (
                RUBRIC_PATH,
                Q14_PATH,
                PLANT_KEY_PATH,
                SCRIPT_PATH,
                PROTOCOL_PATH,
                CALIBRATION_PATH,
                GUIDANCE_PATH,
                AMENDMENT_PATH,
            )
        },
        "question_spec_sha256": _payload_sha256(
            {
                "criteria": CRITERIA,
                "credit_catalog": CREDIT_CATALOG,
                "allowed_scores": ALLOWED_SCORES,
                "turn_by_question": TURN_BY_QUESTION,
            }
        ),
        "h3_status": "NOT_EVALUABLE_NO_ORIGINAL_SCORE",
        "h5_seed": H5_SEED,
    }
    write_json(PREFLIGHT_PATH, payload)
    if payload["status"] != "PASS":
        raise RuntimeError("Tier 6 scoring preflight failed")
    return payload


def prepare_scoring() -> dict:
    if EVALUATION_ROOT.exists():
        raise RuntimeError(
            f"Refusing to overwrite scoring directory {EVALUATION_ROOT}"
        )
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight["status"] != "PASS" or not _is_tracked(PREFLIGHT_PATH):
        raise RuntimeError("Committed PASS scoring preflight is required")

    manifest = json.loads(LAUNCH_MANIFEST.read_text(encoding="utf-8"))
    surface = json.loads(SCORING_SURFACE.read_text(encoding="utf-8"))
    seal = json.loads(MECHANISM_SEAL.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise RuntimeError("Tier 6 live launch manifest is not complete")
    if manifest.get("phase") != "live" or manifest.get("max_turns") != 121:
        raise RuntimeError("Scoring source is not the registered live run")
    if manifest.get("run_id") != RUN_ID:
        raise RuntimeError("Unexpected Tier 6 live run ID")
    if manifest["scoring_surface_sha256"] != sha256(SCORING_SURFACE):
        raise RuntimeError("Scoring-surface hash differs from launch manifest")
    if manifest["mechanism_seal_sha256"] != sha256(MECHANISM_SEAL):
        raise RuntimeError("Mechanism-seal hash differs from launch manifest")
    if seal.get("status") != "SEALED_BEFORE_SCORING":
        raise RuntimeError("Mechanism outputs were not sealed before scoring")
    if surface.get("completeness_status") != "PASS":
        raise RuntimeError("Live scoring-surface completeness gate failed")
    expected_turns = list(range(112, 122))
    if surface.get("expected_turns") != expected_turns:
        raise RuntimeError("Scoring surface has the wrong expected turns")
    if surface.get("observed_turns") != expected_turns:
        raise RuntimeError("Scoring surface is missing rubric turns")
    _verify_surface_payload_hash(surface)

    responses = {
        int(row["turn_number"]): row for row in surface["responses"]
    }
    completeness = {
        int(row["turn_number"]): row for row in surface["completeness"]
    }
    surface_hash = sha256(SCORING_SURFACE)
    anonymous_arm = f"arm_{surface_hash[:10]}"
    item_rows = []
    packet_rows = []
    for question_id in QUESTION_ORDER:
        answer = answer_for_question(question_id, responses)
        completion = question_completeness(
            question_id,
            answer,
            completeness,
        )
        mechanical = mechanical_evidence(question_id, answer)
        anon_id = "RB6-" + hashlib.sha256(
            f"{surface_hash}:{question_id}".encode("ascii")
        ).hexdigest()[:12].upper()
        source_turns = list(TURN_BY_QUESTION[question_id])
        packet = {
            "anon_id": anon_id,
            "anonymous_arm": anonymous_arm,
            "question": question_for_item(question_id, responses),
            "criterion": CRITERIA[question_id],
            "guidance": _guidance(question_id),
            "allowed_scores": list(ALLOWED_SCORES[question_id]),
            "credit_item_catalog": [
                {"id": item_id, "description": description}
                for item_id, description in CREDIT_CATALOG[
                    question_id
                ].items()
            ],
            "answer": answer,
        }
        packet_rows.append(packet)
        item_rows.append(
            {
                "anon_id": anon_id,
                "question_id": question_id,
                "source_turns": source_turns,
                "answer_sha256": hashlib.sha256(
                    answer.encode("utf-8")
                ).hexdigest(),
                "no_answer": completion["no_answer"],
                "truncated": completion["truncated"],
                "unclosed_reasoning": completion["unclosed_reasoning"],
                "mechanical_supported_item_ids": mechanical[
                    "supported_item_ids"
                ],
                "mechanical_evidence": mechanical["evidence"],
                "mechanical_notes": mechanical["notes"],
            }
        )

    EVALUATION_ROOT.mkdir(parents=True)
    write_jsonl(EVALUATION_ROOT / "blind_corpus.jsonl", packet_rows)
    write_jsonl(
        EVALUATION_ROOT / "layer1_fact_presence.jsonl",
        item_rows,
    )
    packet_dir = EVALUATION_ROOT / "pass_packets"
    packet_dir.mkdir()
    for pass_number in (1, 2, 3):
        ordered = sorted(
            packet_rows,
            key=lambda row: _seeded_digest(
                f"{PASS_SEED}:pass-{pass_number}",
                row["anon_id"],
            ),
        )
        write_jsonl(packet_dir / f"pass_{pass_number}.jsonl", ordered)

    write_json(
        EVALUATION_ROOT / "calibration_packet.json",
        blind_calibration_payload(),
    )
    secret = secrets.token_hex(32)
    private_mapping = {
        "secret": secret,
        "anonymous_arm": anonymous_arm,
        "source_arm": "tier6_context_matched_stm",
        "run_id": RUN_ID,
        "source_scoring_surface": _relative(SCORING_SURFACE),
    }
    mapping_commitment = _payload_sha256(private_mapping)
    write_json(
        EVALUATION_ROOT / "private_mapping.json",
        private_mapping,
    )
    write_json(
        EVALUATION_ROOT / "sealed_mapping_commitments.json",
        {
            "sealed": True,
            "algorithm": "SHA-256 over canonical private mapping JSON",
            "mapping_commitment": mapping_commitment,
            "anonymous_arm": anonymous_arm,
            "do_not_open": (
                "Do not stage or open private_mapping.json until "
                "blinded_scores.json is committed."
            ),
        },
    )
    preparation = {
        "status": "READY_FOR_BLIND_RATING",
        "run_id": RUN_ID,
        "anonymous_arm": anonymous_arm,
        "item_count": len(packet_rows),
        "completeness_item_count": len(item_rows),
        "mechanism_seal_status": seal["status"],
        "mechanism_aggregate_sha256": seal["aggregate_sha256"],
        "scoring_surface_sha256": surface_hash,
        "blind_corpus_sha256": sha256(
            EVALUATION_ROOT / "blind_corpus.jsonl"
        ),
        "layer1_sha256": sha256(
            EVALUATION_ROOT / "layer1_fact_presence.jsonl"
        ),
        "pass_packet_sha256": {
            str(number): sha256(
                packet_dir / f"pass_{number}.jsonl"
            )
            for number in (1, 2, 3)
        },
        "calibration_sha256": sha256(
            EVALUATION_ROOT / "calibration_packet.json"
        ),
        "mapping_commitment": mapping_commitment,
        "mapping_opened": False,
        "mechanism_logs_opened": False,
        "h3_status": "NOT_EVALUABLE_NO_ORIGINAL_SCORE",
        "h5_seed": H5_SEED,
    }
    write_json(EVALUATION_ROOT / "preparation_manifest.json", preparation)
    return preparation


def blind_calibration_payload() -> dict:
    source = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    return {
        "metadata": {
            "synthetic": True,
            "expected_scores_withheld": True,
        },
        "items": [
            {
                "id": item["id"],
                "criterion": item["criterion"],
                "scoring_reference": CALIBRATION_REFERENCES[item["id"]],
                "response": item["response"],
            }
            for item in source["items"]
        ],
    }


def refresh_calibration_packet() -> dict:
    result_paths = (
        EVALUATION_ROOT / "calibration",
        EVALUATION_ROOT / "passes",
        EVALUATION_ROOT / "adjudication",
    )
    if any(
        path.exists() and any(path.iterdir())
        for path in result_paths
    ):
        raise RuntimeError(
            "Refusing to refresh calibration after rating began"
        )
    packet_path = EVALUATION_ROOT / "calibration_packet.json"
    manifest_path = EVALUATION_ROOT / "preparation_manifest.json"
    if not packet_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("Tier 6 scoring packet is not prepared")
    write_json(packet_path, blind_calibration_payload())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["calibration_sha256"] = sha256(packet_path)
    manifest["calibration_expected_scores_withheld"] = True
    write_json(manifest_path, manifest)
    return {
        "status": "BLIND_CALIBRATION_READY",
        "calibration_sha256": manifest["calibration_sha256"],
        "item_count": len(blind_calibration_payload()["items"]),
    }


def validate_calibration_result(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    source = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    expected = {row["id"]: row for row in source["items"]}
    rows = payload.get("items")
    if not isinstance(rows, list):
        raise ValueError("Calibration result requires an items list")
    observed = {row.get("id"): row for row in rows}
    if set(observed) != set(expected):
        raise ValueError("Calibration result has the wrong item IDs")
    failures = []
    for item_id, expected_row in expected.items():
        row = observed[item_id]
        primary = _score(row.get("primary"))
        strict = _score(row.get("strict", primary))
        expected_primary = float(expected_row["expected"])
        expected_strict = float(
            expected_row.get("strict_expected", expected_primary)
        )
        if primary != expected_primary or strict != expected_strict:
            failures.append(
                {
                    "id": item_id,
                    "expected": [expected_primary, expected_strict],
                    "observed": [primary, strict],
                }
            )
        if not str(row.get("rationale") or "").strip():
            failures.append({"id": item_id, "error": "missing rationale"})
    if failures:
        raise ValueError(f"Calibration failed: {failures}")
    return {
        "status": "PASS",
        "item_count": len(expected),
        "result_sha256": sha256(path),
    }


def validate_rating_file(
    result_path: Path,
    packet_path: Path,
) -> dict[str, dict]:
    packets = {row["anon_id"]: row for row in read_jsonl(packet_path)}
    rows = read_jsonl(result_path)
    observed = {row.get("anon_id"): row for row in rows}
    if set(observed) != set(packets):
        missing = sorted(set(packets) - set(observed))
        extra = sorted(set(observed) - set(packets))
        raise ValueError(
            f"Rating item mismatch; missing={missing}, extra={extra}"
        )
    for anon_id, row in observed.items():
        packet = packets[anon_id]
        primary = _score(row.get("primary"))
        strict = _score(row.get("strict", primary))
        allowed = {float(value) for value in packet["allowed_scores"]}
        if primary not in allowed or strict not in allowed:
            raise ValueError(f"{anon_id} has a disallowed score")
        if not str(row.get("rationale") or "").strip():
            raise ValueError(f"{anon_id} is missing a rationale")
        catalog = {
            item["id"] for item in packet["credit_item_catalog"]
        }
        primary_ids = _string_set(
            row.get("primary_credited_item_ids", [])
        )
        strict_ids = _string_set(
            row.get("strict_credited_item_ids", primary_ids)
        )
        if not primary_ids <= catalog or not strict_ids <= catalog:
            raise ValueError(f"{anon_id} credits an unknown item")
        if not strict_ids <= primary_ids:
            raise ValueError(
                f"{anon_id} strict credits must be a subset of primary"
            )
        semantic = row.get("semantic_evidence", {})
        if not isinstance(semantic, dict):
            raise ValueError(f"{anon_id} semantic_evidence must be an object")
        if not set(semantic) <= primary_ids:
            raise ValueError(
                f"{anon_id} semantic evidence names an uncredited item"
            )
        for item_id, quote in semantic.items():
            if (
                len(normalize(str(quote))) < 3
                or normalize(str(quote)) not in normalize(packet["answer"])
            ):
                raise ValueError(
                    f"{anon_id}/{item_id} evidence is not a verbatim quote"
                )
    return observed


def analyze_passes() -> dict:
    _require_prepared()
    layer1_rows = read_jsonl(
        EVALUATION_ROOT / "layer1_fact_presence.jsonl"
    )
    layer1 = {row["anon_id"]: row for row in layer1_rows}
    packets = {
        row["anon_id"]: row
        for row in read_jsonl(EVALUATION_ROOT / "blind_corpus.jsonl")
    }
    passes = {}
    calibration = {}
    for pass_number in (1, 2, 3):
        calibration_path = (
            EVALUATION_ROOT
            / "calibration"
            / f"pass_{pass_number}.json"
        )
        calibration[str(pass_number)] = validate_calibration_result(
            calibration_path
        )
        passes[pass_number] = validate_rating_file(
            EVALUATION_ROOT / "passes" / f"pass_{pass_number}.jsonl",
            EVALUATION_ROOT
            / "pass_packets"
            / f"pass_{pass_number}.jsonl",
        )

    consensus_rows = []
    for anon_id, item in sorted(
        layer1.items(),
        key=lambda pair: pair[1]["question_id"],
    ):
        question_id = item["question_id"]
        pass_rows = [passes[number][anon_id] for number in (1, 2, 3)]
        primary_values = [
            _score(row["primary"]) for row in pass_rows
        ]
        strict_values = [
            _score(row.get("strict", row["primary"])) for row in pass_rows
        ]
        primary = float(median(primary_values))
        strict = float(median(strict_values))
        triggers = []
        h1_details = []
        for pass_number, row in enumerate(pass_rows, start=1):
            conflicts = _rating_conflicts(
                question_id,
                packets[anon_id],
                item,
                row,
            )
            if conflicts:
                h1_details.append(
                    {"pass": pass_number, "conflicts": conflicts}
                )
        if h1_details:
            triggers.append("H1")
        self_consistent = (
            len(set(primary_values)) == 1
            and len(set(strict_values)) == 1
        )
        if not self_consistent:
            triggers.append("H2")
        if question_id in {"Q11", "Q14"}:
            triggers.append("H4")
        consensus_rows.append(
            {
                "anon_id": anon_id,
                "question_id": question_id,
                "pass_primary": primary_values,
                "pass_strict": strict_values,
                "primary_consensus": primary,
                "strict_consensus": strict,
                "self_consistent": self_consistent,
                "h1_details": h1_details,
                "triggers": triggers,
            }
        )

    eligible_h5 = [
        row
        for row in consensus_rows
        if row["self_consistent"]
        and not {"H1", "H2", "H4"} & set(row["triggers"])
    ]
    eligible_h5.sort(
        key=lambda row: _seeded_digest(H5_SEED, row["anon_id"])
    )
    h5_count = math.ceil(0.10 * len(eligible_h5)) if eligible_h5 else 0
    for row in eligible_h5[:h5_count]:
        row["triggers"].append("H5")

    write_jsonl(
        EVALUATION_ROOT / "consensus_and_triggers.jsonl",
        consensus_rows,
    )
    independent_ids = {
        row["anon_id"]
        for row in consensus_rows
        if {"H4", "H5"} & set(row["triggers"])
    }
    conflict_ids = {
        row["anon_id"]
        for row in consensus_rows
        if {"H1", "H2"} & set(row["triggers"])
        and row["anon_id"] not in independent_ids
    }
    independent_packet = [
        {
            **packets[anon_id],
            "trigger_class": "H4/H5 independent-before-reveal",
        }
        for anon_id in sorted(independent_ids)
    ]
    write_jsonl(
        EVALUATION_ROOT / "independent_adjudication_packet.jsonl",
        independent_packet,
    )
    conflict_packet = []
    consensus_by_id = {row["anon_id"]: row for row in consensus_rows}
    for anon_id in sorted(conflict_ids):
        conflict_packet.append(
            {
                **packets[anon_id],
                "trigger_class": "H1/H2 visible-conflict adjudication",
                "pass_results": [
                    passes[number][anon_id] for number in (1, 2, 3)
                ],
                "layer1_evidence": layer1[anon_id],
                "consensus": consensus_by_id[anon_id],
            }
        )
    write_jsonl(
        EVALUATION_ROOT / "conflict_adjudication_packet.jsonl",
        conflict_packet,
    )
    summary = {
        "status": "READY_FOR_INDEPENDENT_ADJUDICATION",
        "calibration": calibration,
        "item_count": len(consensus_rows),
        "self_consistent_count": sum(
            row["self_consistent"] for row in consensus_rows
        ),
        "trigger_counts": {
            trigger: sum(
                trigger in row["triggers"] for row in consensus_rows
            )
            for trigger in ("H1", "H2", "H4", "H5")
        },
        "h3_status": "NOT_EVALUABLE_NO_ORIGINAL_SCORE",
        "h5_seed": H5_SEED,
        "h5_eligible_count": len(eligible_h5),
        "h5_selected_count": h5_count,
        "independent_packet_count": len(independent_packet),
        "conflict_packet_count": len(conflict_packet),
    }
    write_json(EVALUATION_ROOT / "trigger_summary.json", summary)
    return summary


def finalize_scores() -> dict:
    consensus_rows = read_jsonl(
        EVALUATION_ROOT / "consensus_and_triggers.jsonl"
    )
    layer1 = {
        row["anon_id"]: row
        for row in read_jsonl(
            EVALUATION_ROOT / "layer1_fact_presence.jsonl"
        )
    }
    passes = {
        number: validate_rating_file(
            EVALUATION_ROOT / "passes" / f"pass_{number}.jsonl",
            EVALUATION_ROOT
            / "pass_packets"
            / f"pass_{number}.jsonl",
        )
        for number in (1, 2, 3)
    }
    validate_calibration_result(
        EVALUATION_ROOT / "calibration" / "adjudicator.json"
    )
    independent_packet = (
        EVALUATION_ROOT / "independent_adjudication_packet.jsonl"
    )
    conflict_packet = (
        EVALUATION_ROOT / "conflict_adjudication_packet.jsonl"
    )
    independent = validate_rating_file(
        EVALUATION_ROOT / "adjudication" / "independent.jsonl",
        independent_packet,
    )
    conflict = validate_rating_file(
        EVALUATION_ROOT / "adjudication" / "conflicts.jsonl",
        conflict_packet,
    )
    anonymous_arm = json.loads(
        (
            EVALUATION_ROOT / "preparation_manifest.json"
        ).read_text(encoding="utf-8")
    )["anonymous_arm"]

    scores = {}
    for row in consensus_rows:
        anon_id = row["anon_id"]
        question_id = row["question_id"]
        if anon_id in independent:
            selected = independent[anon_id]
            basis = "independent_ai_adjudicator_h4_h5"
        elif anon_id in conflict:
            selected = conflict[anon_id]
            basis = "independent_ai_adjudicator_h1_h2"
        else:
            primary = float(row["primary_consensus"])
            strict = float(row["strict_consensus"])
            selected = next(
                pass_rows[anon_id]
                for pass_rows in passes.values()
                if _score(pass_rows[anon_id]["primary"]) == primary
                and _score(
                    pass_rows[anon_id].get(
                        "strict",
                        pass_rows[anon_id]["primary"],
                    )
                )
                == strict
            )
            basis = "three_pass_consensus"
        primary = _score(selected["primary"])
        strict = _score(selected.get("strict", primary))
        answer = _packet_by_id()[anon_id]["answer"]
        validate_score(
            score=primary,
            response=answer,
            rationale=str(selected["rationale"]),
            generation_cap_hit=bool(layer1[anon_id]["truncated"]),
        )
        validate_score(
            score=strict,
            response=answer,
            rationale=str(selected["rationale"]),
            generation_cap_hit=bool(layer1[anon_id]["truncated"]),
        )
        scores[question_id] = {
            "anon_id": anon_id,
            "primary": primary,
            "strict": strict,
            "basis": basis,
            "triggers": row["triggers"],
            "rationale": str(selected["rationale"]),
            "primary_credited_item_ids": sorted(
                _string_set(
                    selected.get("primary_credited_item_ids", [])
                )
            ),
            "strict_credited_item_ids": sorted(
                _string_set(
                    selected.get(
                        "strict_credited_item_ids",
                        selected.get("primary_credited_item_ids", []),
                    )
                )
            ),
        }

    q1_q13_primary = sum(
        scores[f"Q{number}"]["primary"] for number in range(1, 14)
    )
    q1_q13_strict = sum(
        scores[f"Q{number}"]["strict"] for number in range(1, 14)
    )
    category_ranges = {
        "cat1_Q1_Q3": range(1, 4),
        "cat2_Q4_Q6": range(4, 7),
        "cat3_Q7_Q8": range(7, 9),
        "cat4_Q9_Q11": range(9, 12),
        "cat5_Q12_Q13": range(12, 14),
    }
    payload = {
        "status": "FINAL_BLINDED_SCORES",
        "anonymous_arm": anonymous_arm,
        "mapping_opened_before_scoring": False,
        "mechanism_logs_opened_before_scoring": False,
        "rater_class": "three independent clean-context AI passes",
        "adjudicator_class": "fourth independent clean-context AI",
        "adjudicator_limitation": (
            "The adjudicator is an AI, not a human."
        ),
        "calibration_pass_count": 4,
        "h3_status": "NOT_EVALUABLE_NO_ORIGINAL_SCORE",
        "scores": scores,
        "q1_q13_primary": q1_q13_primary,
        "q1_q13_strict": q1_q13_strict,
        "q14_primary": scores["Q14"]["primary"],
        "q14_strict": scores["Q14"]["strict"],
        "category_primary": {
            name: sum(
                scores[f"Q{number}"]["primary"] for number in numbers
            )
            for name, numbers in category_ranges.items()
        },
        "category_strict": {
            name: sum(
                scores[f"Q{number}"]["strict"] for number in numbers
            )
            for name, numbers in category_ranges.items()
        },
        "study_009_arm_l_corrected_target": 12.0,
        "t6_1000_turn_decision": (
            "NOT_RUN_SCORE_AT_LEAST_12"
            if q1_q13_primary >= 12.0
            else "RUN_REQUIRED_SCORE_BELOW_12"
        ),
        "mechanical_fact_presence_artifact": (
            "layer1_fact_presence.jsonl"
        ),
        "trigger_artifact": "consensus_and_triggers.jsonl",
    }
    write_json(EVALUATION_ROOT / "blinded_scores.json", payload)
    return payload


def unseal_scores() -> dict:
    score_path = EVALUATION_ROOT / "blinded_scores.json"
    if not _is_tracked(score_path):
        raise RuntimeError("Blinded scores must be committed before unsealing")
    changed = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", _relative(score_path)],
        cwd=REPO_ROOT,
        check=False,
    )
    if changed.returncode != 0:
        raise RuntimeError("Committed blinded scores differ from the worktree")
    private_mapping = json.loads(
        (EVALUATION_ROOT / "private_mapping.json").read_text(
            encoding="utf-8"
        )
    )
    commitment = json.loads(
        (
            EVALUATION_ROOT / "sealed_mapping_commitments.json"
        ).read_text(encoding="utf-8")
    )
    verified = (
        _payload_sha256(private_mapping)
        == commitment["mapping_commitment"]
    )
    if not verified:
        raise RuntimeError("Sealed arm mapping commitment did not verify")
    scores = json.loads(score_path.read_text(encoding="utf-8"))
    payload = {
        "status": "UNSEALED_AFTER_SCORE_COMMIT",
        "commitment_verified": True,
        "anonymous_arm": private_mapping["anonymous_arm"],
        "source_arm": private_mapping["source_arm"],
        "run_id": private_mapping["run_id"],
        "source_scoring_surface": private_mapping[
            "source_scoring_surface"
        ],
        "q1_q13_primary": scores["q1_q13_primary"],
        "q1_q13_strict": scores["q1_q13_strict"],
        "q14_primary": scores["q14_primary"],
        "q14_strict": scores["q14_strict"],
        "t6_1000_turn_decision": scores["t6_1000_turn_decision"],
    }
    write_json(EVALUATION_ROOT / "unsealed_mapping.json", payload)
    return payload


def answer_for_question(
    question_id: str,
    responses: dict[int, dict],
) -> str:
    if question_id == "Q13":
        parts = []
        for turn in range(112, 121):
            parts.append(
                f"## Turn {turn}\n"
                f"{str(responses[turn]['assistant_message']).strip()}"
            )
        return "\n\n".join(parts)
    turn = TURN_BY_QUESTION[question_id][0]
    return str(responses[turn]["assistant_message"])


def question_for_item(
    question_id: str,
    responses: dict[int, dict],
) -> str:
    if question_id == "Q9":
        return (
            "Topic-bleed check on the turn-117 answer: did the Renaissance "
            "retrieval avoid monetary-policy and marine-biology contamination?"
        )
    if question_id == "Q10":
        return (
            "Researcher-disambiguation check on the turn-118 answer: was "
            "Dr. Kenji Watanabe correctly attributed to Vampyroteuthis "
            "infernalis without conflating the named researchers?"
        )
    if question_id == "Q13":
        return (
            "Across turns 112-120, were the applicable behavioral rules "
            "honored in at least five of the nine turns?"
        )
    turn = TURN_BY_QUESTION[question_id][0]
    return str(responses[turn]["user_message"])


def question_completeness(
    question_id: str,
    answer: str,
    completeness: dict[int, dict],
) -> dict:
    rows = [completeness[turn] for turn in TURN_BY_QUESTION[question_id]]
    generation_cap_hit = any(
        bool(row["reached_response_budget"]) for row in rows
    )
    inspected = inspect_completeness(
        answer,
        generation_cap_hit=generation_cap_hit,
    )
    return {
        "no_answer": inspected.no_answer,
        "truncated": inspected.truncated,
        "unclosed_reasoning": inspected.unclosed_reasoning,
    }


def mechanical_evidence(question_id: str, answer: str) -> dict:
    normalized = normalize(answer)
    catalog = CREDIT_CATALOG[question_id]
    supported = set()
    evidence: dict[str, list[str]] = {}
    notes = {}
    for item_id in catalog:
        aliases = ALIASES.get(item_id)
        if aliases and _aliases_match(normalized, aliases):
            supported.add(item_id)
            evidence[item_id] = [
                " + ".join(alias)
                for alias in aliases
                if all(normalize(term) in normalized for term in alias)
            ]

    if question_id == "Q6":
        renaissance = all(
            term in normalized
            for term in ("cardinal", "giuliano", "rovere", "patron")
        ) and (
            "pope julius ii" in normalized
            or ("pope" in normalized and "julius" in normalized)
        )
        bleed_terms = _present_terms(
            normalized,
            (
                "taylor rule",
                "priya mehta",
                "vampyroteuthis",
                "kenji watanabe",
            ),
        )
        notes["bleed_terms_present"] = bleed_terms
        if renaissance and not bleed_terms:
            supported.add("clean_patron_and_pope")
            evidence["clean_patron_and_pope"] = [
                "patron",
                "Pope Julius II",
                "no registered bleed terms",
            ]
    elif question_id == "Q9":
        renaissance = (
            "cardinal" in normalized
            and "rovere" in normalized
            and (
                "patron" in normalized
                or "pope julius ii" in normalized
            )
        )
        bleed_terms = _present_terms(
            normalized,
            (
                "taylor rule",
                "priya mehta",
                "inflation threshold",
                "vampyroteuthis",
                "kenji watanabe",
            ),
        )
        notes["bleed_terms_present"] = bleed_terms
        if renaissance and not bleed_terms:
            supported.add("clean_renaissance_retrieval")
            evidence["clean_renaissance_retrieval"] = [
                "Renaissance anchors present",
                "no registered bleed terms",
            ]
    elif question_id == "Q10":
        correct = (
            "kenji" in normalized
            and "watanabe" in normalized
            and "vampyroteuthis" in normalized
        )
        notes["other_researcher_names_present"] = _present_terms(
            normalized,
            ("anara bekova", "priya mehta"),
        )
        if correct:
            supported.add("correct_watanabe_attribution")
            evidence["correct_watanabe_attribution"] = [
                "Kenji Watanabe",
                "Vampyroteuthis",
            ]
    elif question_id == "Q13":
        numbered_turns = len(
            re.findall(r"(?m)^## Turn \d+\n(?=\s*1[\.\)])", answer)
        )
        risk_labels = len(
            re.findall(
                r"\(Risk:\s*(?:Low|Medium|High)\)",
                answer,
                flags=re.I,
            )
        )
        notes["numbered_turn_count"] = numbered_turns
        notes["risk_label_count"] = risk_labels
        if numbered_turns >= 5:
            supported.add("late_turn_rule_compliance")
            evidence["late_turn_rule_compliance"] = [
                f"{numbered_turns} turns begin with numbered formatting"
            ]
    elif question_id == "Q14":
        _add_q14_evidence(normalized, supported, evidence, notes)

    return {
        "supported_item_ids": sorted(supported),
        "evidence": evidence,
        "notes": notes,
    }


def derive_score(question_id: str, credited: set[str]) -> float:
    count = len(credited)
    if question_id in {"Q1", "Q2", "Q3", "Q5", "Q8"}:
        return 1.0 if count == 2 else 0.5 if count == 1 else 0.0
    if question_id in {"Q4", "Q7"}:
        return 1.0 if count == 4 else 0.5 if count in {2, 3} else 0.0
    if question_id in {"Q6", "Q9", "Q10", "Q13"}:
        return 1.0 if count == 1 else 0.0
    if question_id == "Q11":
        return 1.0 if count >= 14 else 0.0
    if question_id == "Q12":
        return 1.0 if count == 2 else 0.0
    if question_id == "Q14":
        named = {
            domain
            for domain in ("civil", "art", "monetary", "marine")
            if f"q14_{domain}_named" in credited
        }
        hits = {
            domain
            for domain in ("civil", "art", "monetary", "marine")
            if f"q14_{domain}_hit" in credited
        }
        if len(named) == 4 and len(hits) == 4:
            return 1.0
        if len(named) == 4 and len(hits) == 3:
            return 0.5
        return 0.0
    raise KeyError(question_id)


def normalize(value: str) -> str:
    value = (
        value.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .casefold()
    )
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n"
            )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rating_conflicts(
    question_id: str,
    packet: dict,
    layer1: dict,
    rating: dict,
) -> list[str]:
    conflicts = []
    primary = _score(rating["primary"])
    strict = _score(rating.get("strict", primary))
    primary_ids = _string_set(
        rating.get("primary_credited_item_ids", [])
    )
    strict_ids = _string_set(
        rating.get("strict_credited_item_ids", primary_ids)
    )
    if derive_score(question_id, primary_ids) != primary:
        conflicts.append("primary score conflicts with credited-item count")
    if derive_score(question_id, strict_ids) != strict:
        conflicts.append("strict score conflicts with credited-item count")
    supported = set(layer1["mechanical_supported_item_ids"])
    semantic = rating.get("semantic_evidence", {})
    semantic_supported = {
        item_id
        for item_id, quote in semantic.items()
        if normalize(str(quote)) in normalize(packet["answer"])
    }
    unsupported = primary_ids - supported - semantic_supported
    if unsupported:
        conflicts.append(
            "credited items lack mechanical or quoted support: "
            + ", ".join(sorted(unsupported))
        )
    if (layer1["no_answer"] or layer1["truncated"]) and primary > 0:
        conflicts.append("positive score on NO_ANSWER or truncated output")
    return conflicts


def _add_q14_evidence(
    normalized: str,
    supported: set[str],
    evidence: dict[str, list[str]],
    notes: dict,
) -> None:
    domains = {
        "civil": {
            "named": ("civil engineering", "bridge", "halcyon crossing"),
            "specifics": (
                "halcyon crossing",
                "847",
                "s460ml",
                "92.4",
                "anara bekova",
            ),
        },
        "art": {
            "named": ("renaissance art", "painting", "annunciation"),
            "specifics": (
                "annunciation",
                "melozzo",
                "giuliano della rovere",
                "1483",
                "lead white",
                "ultramarine",
            ),
        },
        "monetary": {
            "named": ("monetary policy", "federal reserve", "taylor rule"),
            "specifics": (
                "taylor rule",
                "federal reserve",
                "priya mehta",
                "2.3",
                "2%",
                "dual mandate",
            ),
        },
        "marine": {
            "named": (
                "marine biology",
                "vampyroteuthis",
                "vampire squid",
            ),
            "specifics": (
                "vampyroteuthis",
                "kenji watanabe",
                "600",
                "900",
                "photophore",
                "mantle margin",
                "marine snow",
            ),
        },
    }
    domain_notes = {}
    for domain, values in domains.items():
        named_matches = _present_terms(normalized, values["named"])
        specific_matches = _present_terms(normalized, values["specifics"])
        named_id = f"q14_{domain}_named"
        hit_id = f"q14_{domain}_hit"
        if named_matches:
            supported.add(named_id)
            evidence[named_id] = named_matches
        if named_matches and specific_matches:
            supported.add(hit_id)
            evidence[hit_id] = specific_matches
        domain_notes[domain] = {
            "named_matches": named_matches,
            "specific_matches": specific_matches,
        }
    notes["q14_domains"] = domain_notes
    notes["denial_terms_present"] = _present_terms(
        normalized,
        (
            "not discussed",
            "did not discuss",
            "wasn't discussed",
            "were not discussed",
        ),
    )


def _guidance(question_id: str) -> str:
    base = (
        "Only final content outside reasoning blocks is scoreable. Use only "
        "the supplied answer and criterion. Return primary and strict scores, "
        "an answer-grounded rationale, primary_credited_item_ids, "
        "strict_credited_item_ids, and semantic_evidence. Strict credits must "
        "exclude a correct term offered only as one of unresolved alternatives. "
        "If a credited catalog item is a paraphrase not captured literally, "
        "semantic_evidence must contain a short verbatim answer quote."
    )
    if question_id == "Q11":
        return (
            base
            + " Q11 has a 17-item denominator, needs at least 14 correctly "
            "attributed items, and has no half-credit category."
        )
    if question_id == "Q14":
        return (
            base
            + " Q14 requires recognizable naming of all four domains; extra "
            "specifics in one domain cannot compensate for another."
        )
    return base


def _verify_surface_payload_hash(surface: dict) -> None:
    payload = dict(surface)
    observed = payload.pop("payload_sha256")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    expected = hashlib.sha256(encoded).hexdigest()
    if observed != expected:
        raise RuntimeError("Scoring-surface internal hash did not verify")


def _packet_by_id() -> dict[str, dict]:
    return {
        row["anon_id"]: row
        for row in read_jsonl(EVALUATION_ROOT / "blind_corpus.jsonl")
    }


def _require_prepared() -> None:
    manifest = json.loads(
        (EVALUATION_ROOT / "preparation_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if manifest["status"] != "READY_FOR_BLIND_RATING":
        raise RuntimeError("Tier 6 scoring packet is not ready")
    if manifest["blind_corpus_sha256"] != sha256(
        EVALUATION_ROOT / "blind_corpus.jsonl"
    ):
        raise RuntimeError("Blind corpus changed after preparation")
    if manifest["layer1_sha256"] != sha256(
        EVALUATION_ROOT / "layer1_fact_presence.jsonl"
    ):
        raise RuntimeError("Layer 1 evidence changed after preparation")


def _aliases_match(
    normalized: str,
    aliases: tuple[tuple[str, ...], ...],
) -> bool:
    return any(
        all(normalize(term) in normalized for term in alias)
        for alias in aliases
    )


def _present_terms(normalized: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if normalize(term) in normalized]


def _seeded_digest(seed: str, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def _payload_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _score(value: object) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a score")
    score = float(value)
    if score not in {0.0, 0.5, 1.0}:
        raise ValueError(f"Invalid score {score}")
    return score


def _string_set(value: object) -> set[str]:
    if isinstance(value, set):
        items = value
    elif isinstance(value, (list, tuple)):
        items = set(value)
    else:
        raise ValueError("Credited item IDs must be a list")
    if not all(isinstance(item, str) for item in items):
        raise ValueError("Credited item IDs must be strings")
    return set(items)


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _is_tracked(path: Path) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", _relative(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
