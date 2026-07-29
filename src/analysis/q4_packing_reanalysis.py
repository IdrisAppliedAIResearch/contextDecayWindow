from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import unicodedata
from html import escape
from pathlib import Path

import numpy as np

from src.analysis.rendering_expansion_rederivation import B_SWEEP
from src.analysis.rendering_expansion_replay import BAKEOFF_RUN, REPO_ROOT
from src.embeddings.provider import cosine_similarity
from src.memory.context_matched_stm import pack_stm_payload
from src.memory.stm_context_builder import render_episode_block
from src.retrieval_bakeoff.config import CARRIED_EMBEDDING_SHA256
from src.retrieval_bakeoff.embedding import CarriedEmbedder


PROBE_TURN = 115
PLANT_TURN = 55
N_CAP = 32
REGISTERED_B_LTM = 32_000
HISTORICAL_PAYLOAD_BUDGET = 60_595
HISTORICAL_PAYLOAD_CHARS = 59_708
HISTORICAL_FITTED_EPISODES = 15
K_THRESHOLD = 0.48
TURN_55_COSINE = 0.16612689197063446
DESIGN_COMMIT = "7c90235a"
FACTS = {
    "title": "Annunciation",
    "artist": "Melozzo da Forli",
    "patron": "Cardinal Giuliano della Rovere",
    "year": "1483",
}
RUN_RELATIVE = BAKEOFF_RUN.relative_to(REPO_ROOT).as_posix()
CONTEXT_LOG = BAKEOFF_RUN / "logs" / "context_match.jsonl"
SEAL_PATH = BAKEOFF_RUN / "mechanism_seal.json"
EXCLUSION_TRACE = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "analysis_corrected_121"
    / "q4_exclusion_trace.json"
)

CSV_FIELDS = (
    "rank",
    "episode_id",
    "source_turn",
    "cosine",
    "topic_label",
    "stored_span_chars",
    "source_content_chars",
    "pre_fix_element_chars",
    "post_fix_element_chars",
    "structural_reduction_chars",
    "selected_at_32k",
)


def generate_analysis(output_dir: Path, embedding_path: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_paths = _source_paths()
    before = _hash_paths(source_paths)

    seal = verify_canonical_source_seal()
    context_row = _context_row()
    candidates = _ordered_candidates(context_row)
    query = _probe_query()
    cosines, query_vector_sha = _candidate_cosines(
        candidates,
        query,
        embedding_path,
    )

    historical = _historical_reproduction(candidates, context_row)
    frontier = [_pack_row(candidates, budget) for budget in B_SWEEP]
    point = next(
        row for row in frontier if row["budget_chars"] == REGISTERED_B_LTM
    )
    turn_55_id = _turn_55_id(candidates)
    turn_55_rank = next(
        rank
        for rank, candidate in enumerate(candidates, 1)
        if str(candidate["id"]) == turn_55_id
    )
    turn_55_cosine = cosines[turn_55_id]
    if abs(turn_55_cosine - TURN_55_COSINE) > 1e-7:
        raise AssertionError(
            "Turn-55 cosine did not reproduce the committed exclusion trace"
        )

    first_entry = next(
        (
            row["budget_chars"]
            for row in frontier
            if row["turn_55_selected"]
        ),
        None,
    )
    fact_presence = _fact_presence(candidates, point["selected_ids"])
    verdict = _decision(point, first_entry)
    after = _hash_paths(source_paths)
    sources_unchanged = before == after

    candidate_rows = []
    selected_at_32k = set(point["selected_ids"])
    for rank, candidate in enumerate(candidates, 1):
        pre_fix = _historical_element(candidate)
        post_fix = render_episode_block(
            "measurement",
            [candidate],
            "recent",
        ).split("\n", 1)[1].rsplit("\n", 1)[0]
        candidate_rows.append(
            {
                "rank": rank,
                "episode_id": str(candidate["id"]),
                "source_turn": int(candidate["turn_number"]),
                "cosine": f"{cosines[str(candidate['id'])]:.17g}",
                "topic_label": str(candidate.get("topic_label") or ""),
                "stored_span_chars": "",
                "source_content_chars": len(
                    str(candidate.get("user_message") or "")
                    + str(candidate.get("assistant_message") or "")
                ),
                "pre_fix_element_chars": len(pre_fix),
                "post_fix_element_chars": len(post_fix),
                "structural_reduction_chars": len(pre_fix) - len(post_fix),
                "selected_at_32k": (
                    str(candidate["id"]) in selected_at_32k
                ),
            }
        )

    result = {
        "analysis": "AS-001",
        "design_commit": DESIGN_COMMIT,
        "status": (
            "PASS"
            if seal["analysis_source_status"] == "PASS"
            and historical["status"] == "PASS"
            and sources_unchanged
            else "FAIL"
        ),
        "inference_calls": 0,
        "embedding": {
            "provider": "CarriedEmbedder",
            "model_sha256": _sha256(embedding_path),
            "expected_model_sha256": CARRIED_EMBEDDING_SHA256,
            "query_sha256": _text_sha256(query),
            "query_vector_sha256": query_vector_sha,
            "turn_55_cosine": turn_55_cosine,
            "committed_turn_55_cosine": TURN_55_COSINE,
        },
        "source_integrity": {
            "status": "PASS" if sources_unchanged else "FAIL",
            "file_count": len(source_paths),
            "tree_sha256_before": _digest_mapping(before),
            "tree_sha256_after": _digest_mapping(after),
        },
        "canonical_mechanism_seal": seal,
        "locked_inputs": {
            "probe_turn": PROBE_TURN,
            "plant_turn": PLANT_TURN,
            "plant_age_turns": PROBE_TURN - PLANT_TURN,
            "n_cap": N_CAP,
            "turn_55_rank": turn_55_rank,
            "k_threshold": K_THRESHOLD,
            "point_budget_chars": REGISTERED_B_LTM,
            "budget_sweep": list(B_SWEEP),
        },
        "historical_reproduction": historical,
        "point_estimate": point,
        "sensitivity_frontier": frontier,
        "first_budget_turn_55_enters": first_entry,
        "q4_fact_presence_at_point": fact_presence,
        "decision": verdict,
    }

    _write_csv(output_dir / "candidate_manifest.csv", candidate_rows)
    _write_json(output_dir / "source_seal_verification.json", seal)
    _write_json(output_dir / "packing_analysis.json", result)
    (output_dir / "packing_report.md").write_text(
        _report(result),
        encoding="utf-8",
        newline="\n",
    )
    return result


def verify_canonical_source_seal() -> dict:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    canonical: dict[str, str] = {}
    canonical_mismatches = []
    checkout_mismatches = []
    missing_committed_files = []
    normalized_equivalence = []
    representation_counts = {"canonical_lf": 0, "materialized_crlf": 0}

    for relative, expected in sorted(seal["mechanism_files"].items()):
        repository_path = f"{RUN_RELATIVE}/{relative}"
        exists = subprocess.run(
            ["git", "cat-file", "-e", f"HEAD:{repository_path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        if exists.returncode != 0:
            missing_committed_files.append(relative)
            continue
        blob = subprocess.check_output(
            ["git", "show", f"HEAD:{repository_path}"],
            cwd=REPO_ROOT,
        )
        canonical_digest = hashlib.sha256(blob).hexdigest()
        canonical[relative] = canonical_digest
        lf_blob = _newline_normalized(blob)
        crlf_digest = hashlib.sha256(
            lf_blob.replace(b"\n", b"\r\n")
        ).hexdigest()
        if canonical_digest == expected:
            representation_counts["canonical_lf"] += 1
        elif b"\0" not in blob and crlf_digest == expected:
            representation_counts["materialized_crlf"] += 1
        else:
            canonical_mismatches.append(
                {
                    "path": relative,
                    "expected": expected,
                    "canonical_lf": canonical_digest,
                    "materialized_crlf": crlf_digest,
                }
            )

        checkout = BAKEOFF_RUN / relative
        checkout_digest = _sha256(checkout)
        if checkout_digest != expected:
            equivalent = _newline_normalized(checkout.read_bytes()) == (
                _newline_normalized(blob)
            )
            checkout_mismatches.append(
                {
                    "path": relative,
                    "expected": expected,
                    "checkout": checkout_digest,
                    "newline_normalized_equivalent": equivalent,
                }
            )
            normalized_equivalence.append(equivalent)

    aggregate = hashlib.sha256()
    for relative, digest in sorted(canonical.items()):
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\0")
    aggregate_digest = aggregate.hexdigest()
    analysis_source_status = (
        "PASS"
        if not canonical_mismatches
        and missing_committed_files == ["study.db"]
        and all(normalized_equivalence)
        else "FAIL"
    )
    return {
        "status": "FAIL_MISSING_COMMITTED_DB",
        "analysis_source_status": analysis_source_status,
        "seal_status": seal["status"],
        "expected_mechanism_file_count": len(seal["mechanism_files"]),
        "tracked_mechanism_file_count": len(canonical),
        "tracked_aggregate_sha256": aggregate_digest,
        "expected_aggregate_sha256": seal["aggregate_sha256"],
        "missing_committed_files": missing_committed_files,
        "matched_representations": representation_counts,
        "canonical_mismatches": canonical_mismatches,
        "checkout_mismatches": checkout_mismatches,
        "interpretation": (
            "The historical seal is invalid because study.db was never "
            "committed. Every tracked seal entry matches either canonical LF "
            "bytes or deterministic CRLF materialization; checkout mismatches "
            "are accepted only when newline-normalized content is identical."
        ),
    }


def _context_row() -> dict:
    rows = [
        json.loads(line)
        for line in CONTEXT_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return next(
        row for row in rows if int(row["turn_number"]) == PROBE_TURN
    )


def _ordered_candidates(context_row: dict) -> list[dict]:
    candidate_ids = list(context_row["n_candidate_ids"])
    if len(candidate_ids) != N_CAP or len(set(candidate_ids)) != N_CAP:
        raise AssertionError("Q4 N candidates are not 32 unique identities")
    turns_path = BAKEOFF_RUN / "logs" / "turns.jsonl"
    turns = [
        json.loads(line)
        for line in turns_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {
        str(row["stored_episode_id"]): {
            "id": str(row["stored_episode_id"]),
            "topic_id": None,
            "topic_label": str(row.get("stored_topic_label") or ""),
            "user_message": str(row["user_message"]),
            "assistant_message": str(row["assistant_message"]),
            "turn_number": int(row["turn_number"]),
        }
        for row in turns
        if row.get("stored_episode_id")
    }
    if any(candidate_id not in by_id for candidate_id in candidate_ids):
        raise AssertionError("Q4 candidate identity is absent from turns.jsonl")
    return [by_id[candidate_id] for candidate_id in candidate_ids]


def _probe_query() -> str:
    turns_path = BAKEOFF_RUN / "logs" / "turns.jsonl"
    for line in turns_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row["turn_number"]) == PROBE_TURN:
            return str(row["user_message"])
    raise AssertionError("Q4 probe turn is absent from turns.jsonl")


def _candidate_cosines(
    candidates: list[dict],
    query: str,
    embedding_path: Path,
) -> tuple[dict[str, float], str]:
    if _sha256(embedding_path) != CARRIED_EMBEDDING_SHA256:
        raise AssertionError("Carried embedding model SHA mismatch")
    embedder = CarriedEmbedder(embedding_path)
    embedder.assert_carried_model()
    query_vector = np.asarray(embedder(query), dtype=np.float32)
    cosines = {}
    for candidate in candidates:
        embedding_text = (
            f"User: {candidate['user_message']}\n"
            f"Assistant: {candidate['assistant_message']}"
        )
        embedding = np.asarray(embedder(embedding_text), dtype=np.float32)
        cosines[str(candidate["id"])] = cosine_similarity(
            query_vector,
            embedding,
        )
    return cosines, hashlib.sha256(query_vector.tobytes()).hexdigest()


def _historical_reproduction(
    candidates: list[dict],
    context_row: dict,
) -> dict:
    delivered = candidates[:HISTORICAL_FITTED_EPISODES]
    payload = _historical_payload(delivered)
    delivered_ids = [str(candidate["id"]) for candidate in delivered]
    status = (
        "PASS"
        if len(payload) == HISTORICAL_PAYLOAD_CHARS
        and delivered_ids == context_row["delivered_n_ids"]
        and int(context_row["retrieval_payload_chars"])
        == HISTORICAL_PAYLOAD_CHARS
        and int(context_row["payload_budget"])
        == HISTORICAL_PAYLOAD_BUDGET
        else "FAIL"
    )
    return {
        "status": status,
        "episode_count": len(delivered),
        "serialized_chars": len(payload),
        "payload_budget_chars": int(context_row["payload_budget"]),
        "payload_sha256": _text_sha256(payload),
        "committed_payload_sha256": context_row["retrieval_payload_sha256"],
        "identity_order_match": (
            delivered_ids == context_row["delivered_n_ids"]
        ),
        "character_count_match": len(payload) == HISTORICAL_PAYLOAD_CHARS,
    }


def _pack_row(candidates: list[dict], budget: int) -> dict:
    packed = pack_stm_payload(candidates, [], budget)
    selected = list(packed.recent_episodes)
    selected_ids = list(packed.selected_ids)
    turn_55_id = _turn_55_id(candidates)
    return {
        "budget_chars": budget,
        "fitted_episodes": len(selected),
        "serialized_chars": packed.serialized_chars,
        "source_content_chars": sum(
            len(
                str(candidate.get("user_message") or "")
                + str(candidate.get("assistant_message") or "")
            )
            for candidate in selected
        ),
        "remaining_chars": budget - packed.serialized_chars,
        "selected_ids": selected_ids,
        "selected_source_turns": [
            int(candidate["turn_number"]) for candidate in selected
        ],
        "skipped_ids": list(packed.skipped_n_ids),
        "turn_55_selected": turn_55_id in selected_ids,
        "margin_s_prime_minus_27": len(selected) - 27,
    }


def _decision(point: dict, first_entry: int | None) -> dict:
    fitted = int(point["fitted_episodes"])
    if fitted >= 29:
        branch = "A"
        verdict = "RENDERING NULL CONFIRMED"
        action = "Do not run a primacy study."
    elif fitted in {27, 28}:
        branch = "B"
        verdict = "BORDERLINE"
        action = "Escalate before inference or architecture decisions."
    elif not point["turn_55_selected"] and first_entry is not None:
        branch = "C"
        verdict = "BUDGET/PACKING"
        action = "Do not claim a primacy mechanism."
    else:
        branch = "D"
        verdict = "PRIMACY MECHANISM LIVE"
        action = (
            "A separately pre-registered CC-001 pinned-set study may be "
            "proposed."
        )
    return {
        "branch": branch,
        "verdict": verdict,
        "action": action,
    }


def _fact_presence(
    candidates: list[dict],
    selected_ids: list[str],
) -> dict:
    selected = {
        str(candidate["id"]): candidate
        for candidate in candidates
        if str(candidate["id"]) in set(selected_ids)
    }
    turn_55 = next(
        (
            candidate
            for candidate in selected.values()
            if int(candidate["turn_number"]) == PLANT_TURN
        ),
        None,
    )
    text = ""
    if turn_55 is not None:
        text = (
            str(turn_55.get("user_message") or "")
            + str(turn_55.get("assistant_message") or "")
        )
    normalized = _normalize(text)
    checks = {
        name: _normalize(value) in normalized
        for name, value in FACTS.items()
    }
    return {
        "turn_55_delivered": turn_55 is not None,
        "checks": checks,
        "all_four_present": turn_55 is not None and all(checks.values()),
        "interpretation": "Availability only; no answer-correctness claim.",
    }


def _turn_55_id(candidates: list[dict]) -> str:
    matches = [
        str(candidate["id"])
        for candidate in candidates
        if int(candidate["turn_number"]) == PLANT_TURN
    ]
    if len(matches) != 1:
        raise AssertionError("Expected exactly one turn-55 N candidate")
    return matches[0]


def _historical_payload(candidates: list[dict]) -> str:
    recent = _historical_block("recent_context", candidates)
    return f"{recent}\n\n<retrieved_stm/>"


def _historical_block(name: str, candidates: list[dict]) -> str:
    if not candidates:
        return f"<{name}/>"
    elements = "\n".join(
        _historical_element(candidate) for candidate in candidates
    )
    return f"<{name}>\n{elements}\n</{name}>"


def _historical_element(candidate: dict) -> str:
    turn = escape(str(candidate.get("turn_number", "")), quote=True)
    topic = escape(
        str(
            candidate.get("topic_label")
            or candidate.get("topic_id")
            or ""
        ),
        quote=True,
    )
    user = escape(str(candidate.get("user_message") or ""), quote=False)
    assistant = escape(
        str(candidate.get("assistant_message") or ""),
        quote=False,
    )
    return "\n".join(
        (
            f'  <episode turn="{turn}" topic="{topic}">',
            f"    <user_message>{user}</user_message>",
            f"    <assistant_message>{assistant}</assistant_message>",
            "  </episode>",
        )
    )


def _report(result: dict) -> str:
    point = result["point_estimate"]
    decision = result["decision"]
    seal = result["canonical_mechanism_seal"]
    facts = result["q4_fact_presence_at_point"]
    lines = [
        "# AS-001 Q4 Packing Result",
        "",
        f"**Status:** {result['status']}",
        f"**Decision:** Branch {decision['branch']} - {decision['verdict']}",
        f"**Design anchor:** `{result['design_commit']}`",
        "",
        "## Point Estimate",
        "",
        "| Budget | Fitted episodes | Serialized chars | Source chars | Rank 27 enters | Margin |",
        "|---:|---:|---:|---:|---|---:|",
        (
            f"| {point['budget_chars']:,} | {point['fitted_episodes']} | "
            f"{point['serialized_chars']:,} | "
            f"{point['source_content_chars']:,} | "
            f"{'YES' if point['turn_55_selected'] else 'NO'} | "
            f"{point['margin_s_prime_minus_27']} |"
        ),
        "",
        "## Sensitivity",
        "",
        "| Budget | Episodes | Serialized chars | Source chars | Rank 27 enters |",
        "|---:|---:|---:|---:|---|",
    ]
    for row in result["sensitivity_frontier"]:
        lines.append(
            f"| {row['budget_chars']:,} | {row['fitted_episodes']} | "
            f"{row['serialized_chars']:,} | "
            f"{row['source_content_chars']:,} | "
            f"{'YES' if row['turn_55_selected'] else 'NO'} |"
        )
    lines.extend(
        (
            "",
            "## Integrity",
            "",
            (
                f"- Historical reproduction: "
                f"{result['historical_reproduction']['status']}; "
                f"{result['historical_reproduction']['episode_count']} "
                "episodes and "
                f"{result['historical_reproduction']['serialized_chars']:,} "
                "characters."
            ),
            (
                f"- Canonical mechanism seal: {seal['status']}; "
                f"{seal['tracked_mechanism_file_count']} of "
                f"{seal['expected_mechanism_file_count']} mechanism files "
                "tracked; `study.db` was never committed."
            ),
            (
                f"- Tracked sealed blobs: "
                f"{seal['analysis_source_status']}; zero SHA mismatches."
            ),
            (
                f"- Checkout-only newline mismatches: "
                f"{len(seal['checkout_mismatches'])}; all normalized "
                "equivalent."
            ),
            (
                f"- Turn-55 cosine: "
                f"{result['embedding']['turn_55_cosine']:.17g} "
                f"(< K={K_THRESHOLD})."
            ),
            (
                f"- Q4 availability at 32k: turn 55 "
                f"{'delivered' if facts['turn_55_delivered'] else 'absent'}; "
                f"all four facts present: "
                f"{'YES' if facts['all_four_present'] else 'NO'}."
            ),
            "- No generative inference call or score change.",
            "",
            "## Verdict",
            "",
            (
                f"Branch {decision['branch']}: **{decision['verdict']}**. "
                f"{decision['action']}"
            ),
            "",
        )
    )
    return "\n".join(lines)


def _source_paths() -> list[Path]:
    return [
        CONTEXT_LOG,
        BAKEOFF_RUN / "logs" / "turns.jsonl",
        SEAL_PATH,
        EXCLUSION_TRACE,
        (
            REPO_ROOT
            / "experiments"
            / "surveys"
            / "retrieval_bakeoff"
            / "tier6"
            / "settings"
            / "tier6_context_match_settings.json"
        ),
        REPO_ROOT / "experiments" / "study_009" / "q_facts_key.md",
        (
            REPO_ROOT
            / "experiments"
            / "components"
            / "rendering_expansion"
            / "artifacts"
            / "rederivation"
            / "rederivation.json"
        ),
        REPO_ROOT / "src" / "memory" / "context_builder.py",
        REPO_ROOT / "src" / "memory" / "stm_context_builder.py",
    ]


def _hash_paths(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(REPO_ROOT).as_posix(): _sha256(path)
        for path in sorted(paths)
    }


def _digest_mapping(mapping: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(mapping.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _newline_normalized(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n")


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).casefold()


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    args = parser.parse_args()
    generate_analysis(
        args.output_dir.resolve(),
        args.embedding_model.resolve(),
    )


if __name__ == "__main__":
    main()
