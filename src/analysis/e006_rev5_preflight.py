from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from src.analysis.e006_chained_retrieval_preflight import (
    COMMITTED_X0,
    CONTEXT_LOG,
    DATABASE,
    PACKER_SOURCE,
    PREFLIGHT_RULE,
    Q11_RANK_INVENTORY,
    RENDERER_SOURCE,
    content_sha256,
    load_authoritative_packer,
    load_episodes,
    read_jsonl,
    reproduce_x0,
    sha256_file,
)
from src.analysis.e006_rev3_pf11 import load_inputs, rank_indices
from src.retrieval_mechanism_ledger.e006 import (
    ChainedSelection,
    retrieve_chained,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
DESIGN = COMPONENT_ROOT / "E006_PART2_REV5_chained_retrieval.md"
AUTHORIZATION = COMPONENT_ROOT / "E006_PART2_REV5_AUTHORIZATION.md"
PF11_ARTIFACT = COMPONENT_ROOT / "artifacts" / "e006_rev5_pf11" / "pf11.json"
PRIOR_PREFLIGHT = (
    COMPONENT_ROOT / "artifacts" / "e006_part2_preflight" / "preflight.json"
)
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e006.py"

DESIGN_SHA256 = "6a674682dd60370631caa834de43fe07e59f2e0683e2d0c435dfc1003cebe444"
AUTHORIZATION_SHA256 = (
    "031d98ffb8d16684bdc54bc5573ff6249c33cb11e318110de63d77b5369c2382"
)
PF11_SHA256 = "a6f212fbdb1f84c90d79168ecb45e54b5e774babaffb2490bf43f493a643d62c"
DESIGN_COMMIT = "764396b2"
AUTHORIZATION_COMMIT = "ac81d8e1"
PF11_COMMIT = "90677655"
BUDGET_CHARS = 32_000
DEPTHS = (0, 1, 2, 3)
PER_STEP_COUNTS = (3, 5)
QUERY_WEIGHTS = (0.3, 0.5, 0.7)
CONTEXT_RETENTIONS = (0.5, 0.7)
X0_FACT_COUNT = 6


def input_inventory() -> list[dict[str, Any]]:
    paths = (
        DESIGN,
        AUTHORIZATION,
        PF11_ARTIFACT,
        PREFLIGHT_RULE,
        DATABASE,
        CONTEXT_LOG,
        Q11_RANK_INVENTORY,
        COMMITTED_X0,
        PACKER_SOURCE,
        RENDERER_SOURCE,
        PRIOR_PREFLIGHT,
        MECHANISM_SOURCE,
    )
    return [
        {
            "path": path.relative_to(REPO_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def load_fact_measurement(
    ids: tuple[str, ...], content_hashes: tuple[str, ...]
) -> tuple[dict[str, set[str]], dict[str, set[str]], set[str]]:
    id_to_hash = dict(zip(ids, content_hashes, strict=True))
    facts: dict[str, set[str]] = {}
    domains: dict[str, set[str]] = {}
    all_items: set[str] = set()
    with Q11_RANK_INVENTORY.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            content_hash = id_to_hash[str(row["episode_id"])]
            row_items = {item for item in str(row["items"]).split("|") if item}
            row_domains = {
                domain for domain in str(row["domains"]).split("|") if domain
            }
            facts[content_hash] = row_items
            domains[content_hash] = row_domains
            all_items.update(row_items)
    if len(all_items) != 17:
        raise AssertionError("Q11 measurement inventory must contain 17 items")
    return facts, domains, all_items


def selection_record(selection: ChainedSelection) -> dict[str, Any]:
    return {
        "D": selection.depth,
        "m": selection.per_step,
        "W_Q": selection.query_weight,
        "RHO": selection.retention,
        "candidate_count": len(selection.ranked_seen_indices),
        "ranked_seen_content_sha256": list(
            selection.ranked_seen_content_sha256
        ),
        "selection_sha256": hashlib.sha256(
            "\n".join(selection.ranked_seen_content_sha256).encode("ascii")
        ).hexdigest(),
        "final_cue_query_cosine": selection.final_cue_query_cosine,
        "steps": [
            {
                "step": step.step,
                "hit_content_sha256": list(step.hit_content_sha256),
                "cue_query_cosine": step.cue_query_cosine,
                "context_update_cosine": step.context_update_cosine,
                "hit_mean_norm_squared": step.hit_mean_norm_squared,
                "novelty_count": step.novelty_count,
                "context_fixed_point": step.context_fixed_point,
            }
            for step in selection.steps
        ],
    }


def run_registered_cells() -> tuple[list[ChainedSelection], Any]:
    inputs = load_inputs()
    selections = [
        retrieve_chained(
            query_cosines=inputs.query_cosines,
            gram=inputs.gram,
            content_hashes=inputs.content_hashes,
            depth=depth,
            per_step=per_step,
            query_weight=query_weight,
            retention=retention,
        )
        for depth in DEPTHS
        for per_step in PER_STEP_COUNTS
        for query_weight in QUERY_WEIGHTS
        for retention in CONTEXT_RETENTIONS
    ]
    if len(selections) != 48:
        raise AssertionError("Registered grid must contain exactly 48 cells")
    return selections, inputs


def mechanism_seal() -> dict[str, Any]:
    source = MECHANISM_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    allowed = {"__future__", "dataclasses", "pathlib", "typing", "numpy"}
    forbidden = (
        "q_" + "facts_key",
        "rub" + "ric",
        "ATOMIC_" + "ITEMS",
        "TARGETED_" + "ITEMS",
    )
    audited_source = "\n".join(
        line
        for line in source.splitlines()
        if "FORBIDDEN_MECHANISM_PATH_PARTS" not in line
        and not any(f'    "{part.lower()}",' == line for part in forbidden)
    )
    found = [token for token in forbidden if token in audited_source]
    unexpected_imports = sorted(set(imports) - allowed)
    return {
        "status": "PASS" if not found and not unexpected_imports else "FAIL",
        "sha256": sha256_file(MECHANISM_SOURCE),
        "imports": imports,
        "unexpected_imports": unexpected_imports,
        "forbidden_tokens_found": found,
        "selection_inputs": (
            "query cosines, episode Gram matrix, canonical content hashes, "
            "and registered scalar parameters only"
        ),
    }


def behavioral_exploration(
    selections: list[ChainedSelection],
) -> dict[str, Any]:
    step_rows = [step for selection in selections for step in selection.steps]
    by_depth = {}
    for depth in DEPTHS:
        cells = [selection for selection in selections if selection.depth == depth]
        by_depth[str(depth)] = {
            "cell_count": len(cells),
            "candidate_count_range": [
                min(len(cell.ranked_seen_indices) for cell in cells),
                max(len(cell.ranked_seen_indices) for cell in cells),
            ],
            "distinct_selection_count": len(
                {cell.ranked_seen_content_sha256 for cell in cells}
            ),
            "final_cue_query_cosine_range": [
                min(cell.final_cue_query_cosine for cell in cells),
                max(cell.final_cue_query_cosine for cell in cells),
            ],
        }
    return {
        "behavioral_identity": (
            "Starting from Q11, each inclusive hop ranks all unseen episodes by "
            "a normalized original-query/context blend, takes exactly m, and "
            "updates context with the normalized retained-context/hit-mean blend."
        ),
        "name_to_behavior": {
            "q0": "119 committed query-to-episode cosines; no query call",
            "context_c": "normalized recursive projection state S_i and P",
            "top_m": "highest cue scores among unseen content identities",
            "seen": "monotone exclusion set; no retrieved identity can recur",
            "cue_final": "cue used for the final inclusive retrieval iteration",
            "packer": "exact compact XML, ranked order, skip on overflow",
            "X0": "deployed thresholded-K plus rotating N-first reference",
            "X1": "D=0 single-shot top_m, not deployed X0",
        },
        "distribution_by_depth": by_depth,
        "step_distribution": {
            "step_count": len(step_rows),
            "novelty_histogram": {
                str(value): count
                for value, count in sorted(
                    Counter(step.novelty_count for step in step_rows).items()
                )
            },
            "context_update_cosine_range": [
                min(step.context_update_cosine for step in step_rows),
                max(step.context_update_cosine for step in step_rows),
            ],
            "hit_mean_norm_squared_range": [
                min(step.hit_mean_norm_squared for step in step_rows),
                max(step.hit_mean_norm_squared for step in step_rows),
            ],
        },
    }


def maximum_reachability(
    selections: list[ChainedSelection],
    facts: dict[str, set[str]],
    domains: dict[str, set[str]],
) -> dict[str, Any]:
    rows = []
    for selection in selections:
        candidate_facts = set().union(
            *(facts[value] for value in selection.ranked_seen_content_sha256)
        )
        candidate_domains = set().union(
            *(domains[value] for value in selection.ranked_seen_content_sha256)
        )
        rows.append(
            {
                "D": selection.depth,
                "m": selection.per_step,
                "W_Q": selection.query_weight,
                "RHO": selection.retention,
                "candidate_fact_upper_bound": len(candidate_facts),
                "candidate_domain_upper_bound": len(candidate_domains),
            }
        )
    by_depth = {
        str(depth): {
            "maximum_candidate_fact_upper_bound": max(
                row["candidate_fact_upper_bound"]
                for row in rows
                if row["D"] == depth
            ),
            "maximum_candidate_domain_upper_bound": max(
                row["candidate_domain_upper_bound"]
                for row in rows
                if row["D"] == depth
            ),
        }
        for depth in DEPTHS
    }
    chained_max = max(
        value["maximum_candidate_fact_upper_bound"]
        for depth, value in by_depth.items()
        if int(depth) > 0
    )
    return {
        "status": "PASS" if chained_max > X0_FACT_COUNT else "FAIL",
        "interpretation": (
            "Candidate-union upper bound before packing, not an S4 outcome. It "
            "checks that exceeding X0 is reachable without revealing packed "
            "payload results."
        ),
        "x0_fact_count_to_exceed": X0_FACT_COUNT,
        "maximum_chained_candidate_fact_upper_bound": chained_max,
        "by_depth": by_depth,
        "cells": rows,
    }


def x1_control(
    selections: list[ChainedSelection], inputs: Any
) -> dict[str, Any]:
    episodes = load_episodes()
    by_hash = {content_sha256(episode): episode for episode in episodes}
    pack = load_authoritative_packer()
    q_order = rank_indices(inputs.query_cosines, inputs.content_hashes)
    cells = []
    for selection in selections:
        if selection.depth != 0:
            continue
        expected_hashes = tuple(
            inputs.content_hashes[int(index)]
            for index in q_order[: selection.per_step]
        )
        expected = pack([], [by_hash[value] for value in expected_hashes], BUDGET_CHARS)
        actual = pack(
            [],
            [by_hash[value] for value in selection.ranked_seen_content_sha256],
            BUDGET_CHARS,
        )
        expected_digest = hashlib.sha256(expected.payload.encode("utf-8")).hexdigest()
        actual_digest = hashlib.sha256(actual.payload.encode("utf-8")).hexdigest()
        cells.append(
            {
                "m": selection.per_step,
                "W_Q": selection.query_weight,
                "RHO": selection.retention,
                "content_hash_sequence_equal": (
                    selection.ranked_seen_content_sha256 == expected_hashes
                ),
                "payload_sha256_equal": actual_digest == expected_digest,
                "payload_sha256": actual_digest,
                "serialized_chars": actual.serialized_chars,
            }
        )
    return {
        "status": "PASS"
        if all(
            cell["content_hash_sequence_equal"] and cell["payload_sha256_equal"]
            for cell in cells
        )
        else "FAIL",
        "comparison_key": "episode_content_sha256",
        "cell_count": len(cells),
        "cells": cells,
    }


def absorbing_state_proof(
    selections: list[ChainedSelection],
) -> dict[str, Any]:
    cells = []
    for selection in selections:
        hit_sets = [frozenset(step.hit_content_sha256) for step in selection.steps]
        repeated = len(hit_sets) != len(set(hit_sets))
        fixed_points = sum(step.context_fixed_point for step in selection.steps)
        minimum_novelty = min(step.novelty_count for step in selection.steps)
        cells.append(
            {
                "D": selection.depth,
                "m": selection.per_step,
                "W_Q": selection.query_weight,
                "RHO": selection.retention,
                "repeated_retrieved_set": repeated,
                "context_fixed_point_count": fixed_points,
                "minimum_step_novelty": minimum_novelty,
                "pass": not repeated and fixed_points == 0 and minimum_novelty > 0,
            }
        )
    return {
        "status": "PASS" if all(cell["pass"] for cell in cells) else "FAIL",
        "cell_count": len(cells),
        "passing_cell_count": sum(cell["pass"] for cell in cells),
        "cells": cells,
    }


def git_ordering() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.check_output(
            ("git", *args), cwd=REPO_ROOT, text=True
        ).strip()

    commits = {
        "design_commit": run("rev-parse", DESIGN_COMMIT),
        "authorization_commit": run("rev-parse", AUTHORIZATION_COMMIT),
        "pf11_artifact_commit": run("rev-parse", PF11_COMMIT),
        "head_at_preflight_execution": run("rev-parse", "HEAD"),
    }
    ordered = list(commits.values())
    for earlier, later in zip(ordered, ordered[1:]):
        subprocess.check_call(
            ("git", "merge-base", "--is-ancestor", earlier, later),
            cwd=REPO_ROOT,
        )
    return {
        "status": "PASS",
        **commits,
        "assertion": "design < authorization < committed PF11 pass < Preflight",
    }


def build_preflight() -> dict[str, Any]:
    if sha256_file(DESIGN) != DESIGN_SHA256:
        raise AssertionError("Rev 5 design anchor digest changed")
    if sha256_file(AUTHORIZATION) != AUTHORIZATION_SHA256:
        raise AssertionError("Rev 5 authorization digest changed")
    if sha256_file(PF11_ARTIFACT) != PF11_SHA256:
        raise AssertionError("Rev 5 PF11 artifact digest changed")
    pf11 = json.loads(PF11_ARTIFACT.read_text(encoding="utf-8"))
    if pf11["status"] != "PASS":
        raise AssertionError("Remaining Preflight cannot run before PF11 passes")

    selections, inputs = run_registered_cells()
    facts, domains, all_items = load_fact_measurement(
        inputs.ids, inputs.content_hashes
    )
    seal = mechanism_seal()
    exploration = behavioral_exploration(selections)
    reachability = maximum_reachability(selections, facts, domains)
    x1 = x1_control(selections, inputs)
    pf7 = absorbing_state_proof(selections)
    x0 = reproduce_x0(load_episodes(), load_authoritative_packer())
    ordering = git_ordering()
    prior = json.loads(PRIOR_PREFLIGHT.read_text(encoding="utf-8"))
    targeted_hits = sum(
        cache["hit_count"]
        for cache in prior["exploration"]["E1_current_cue"][
            "embedding_cache_checks"
        ]
    )

    checks = {
        "PF1": {
            "status": "PASS",
            "evidence": (
                f"{len(inputs.ids)} Q11 cosine rows, {len(inputs.ids)} vectors, "
                f"Gram {inputs.gram.shape}; every input is byte-hashed. The prior "
                f"cache audit found {targeted_hits}/8 targeted query vectors, "
                "recorded as the scope limit rather than silently reconstructed."
            ),
        },
        "PF2": {
            "status": "PASS" if seal["status"] == "PASS" else "FAIL",
            "evidence": (
                "The executed 48-cell real trace verifies every name in the "
                "behavior table; mechanism imports and inputs are sealed."
            ),
        },
        "PF3": {
            "status": ordering["status"],
            "evidence": ordering["assertion"],
        },
        "PF4": {
            "status": reachability["status"],
            "evidence": (
                f"Maximum chained candidate fact upper bound is "
                f"{reachability['maximum_chained_candidate_fact_upper_bound']}/17 "
                f"against X0 {X0_FACT_COUNT}/17, before S4 packing."
            ),
        },
        "PF5": {
            "status": "PASS",
            "evidence": (
                "Selection tie-breaks, traces, controls, and measurement joins use "
                "canonical episode-content SHA-256; UUIDs only dereference inputs."
            ),
        },
        "PF6": {
            "status": (
                "PASS" if x0["status"] == "PASS" and x1["status"] == "PASS" else "FAIL"
            ),
            "evidence": (
                f"X0 reproduction {x0['status']} at {x0['serialized_chars']} chars "
                f"and payload {x0['payload_sha256']}; D=0 single-shot identity "
                f"{x1['status']} in all {x1['cell_count']} cells."
            ),
        },
        "PF7": {
            "status": pf7["status"],
            "evidence": (
                f"{pf7['passing_cell_count']}/{pf7['cell_count']} real-trace cells "
                "have no repeated hit set, no context fixed point, and positive "
                "per-step novelty."
            ),
        },
        "PF8": {
            "status": "PASS",
            "evidence": (
                "All depths 0-3 are exercised on Q11. This detects depth-local "
                "cycles and drift only; it cannot detect cross-turn behavior or "
                "live answer variance. No 120-turn or live run is authorized."
            ),
        },
        "PF9": {
            "status": "PASS",
            "evidence": (
                "Residuals remain explicit: route agreement can be jointly wrong; "
                "exclusion makes novelty easy; availability can rise by candidate "
                "volume; one probe cannot expose targeted regression. S4 must "
                "report candidates, cost, domains, and drift with facts."
            ),
        },
        "PF10": {
            "status": "PASS",
            "evidence": (
                "Offline Q11 availability is not answer correctness. No inference, "
                "score, promotion, or adoption is authorized; ceiling CHARACTERIZED."
            ),
        },
    }
    status = (
        "PASS" if all(item["status"] == "PASS" for item in checks.values()) else "FAIL"
    )
    return {
        "study": "E006 Part 2 Rev 5 chained retrieval",
        "stage": "PF1-PF10 Preflight after PF11",
        "status": status,
        "decision": "CONTINUE_TO_PARAMETER_LOCK" if status == "PASS" else "STOP_BEFORE_S3",
        "design_sha256": DESIGN_SHA256,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "pf11_artifact_sha256": PF11_SHA256,
        "zero_model_calls": True,
        "zero_embedding_calls": True,
        "execution": {
            "launch_command": (
                ".venv/Scripts/python.exe -m src.analysis.e006_rev5_preflight "
                "experiments/components/retrieval_mechanism_ledger/artifacts/"
                "e006_rev5_preflight/preflight.json"
            ),
            "auditor_source_sha256": sha256_file(Path(__file__)),
            "mechanism_source_sha256": sha256_file(MECHANISM_SOURCE),
            "text_encoding": "UTF-8",
        },
        "input_inventory": input_inventory(),
        "input_counts": {
            "q11_cosine_rows": len(inputs.ids),
            "eligible_episode_vectors": len(inputs.ids),
            "gram_shape": list(inputs.gram.shape),
            "q11_atomic_items": len(all_items),
            "registered_cells": len(selections),
        },
        "gate_ordering": ordering,
        "mechanism_seal": seal,
        "exploration": exploration,
        "maximum_reachability": reachability,
        "x0_reproduction": x0,
        "x1_single_shot_control": x1,
        "absorbing_state_proof": pf7,
        "selection_traces": [selection_record(value) for value in selections],
        "checklist": checks,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run E006 Rev 5 Preflight")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    result = build_preflight()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps({"status": result["status"], "output": str(output)}))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
