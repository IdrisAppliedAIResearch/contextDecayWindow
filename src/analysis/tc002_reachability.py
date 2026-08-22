"""TC-002 PF4: are the registered bars reachable, and are they failable?

A paired sign test is decided by its discordant pairs. If two arms never
disagree about whether a question's evidence arrived, no bar on that contrast
can fire in either direction - the defect DMR-001 locked and PF4 exists to
catch. TC-002 registers four contrasts and two budgets, and its Part 1
reconnaissance already showed that the two fill orders deliver an identical set
on a large share of questions at 32,000 characters. Whether that leaves a
reachable bar at EC-002's own budget is precisely what this module measures,
before the budget is chosen.

**What this module deliberately does not compute.** It reports how many
questions each pair of arms disagrees on. It does not report which way they
disagree, and it refuses to write a gains/losses split. A discordant count
establishes that a bar can fire without saying which arm it would fire for, so
it can be read before the bars are locked without section 9.4's rescue risk.
``_forbid_direction`` enforces that boundary on the artifact rather than
trusting this docstring.

Two of these contrasts carry an extra hazard the others do not. TC-001's and
TC-001B's verdicts are public, and ``flat``, ``n_first`` and ``dual`` all appear
in them, so a reader could in principle combine a directional result here with
a published number. That is why nothing directional is emitted for any
contrast, including the ones where it would seem harmless.

Zero model calls; the same read-only, digest-bound cache Part 1 uses.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from analysis.locomo_nf_development import (
    ConversationCase,
    adapt_development,
    sha256_file,
)
from analysis.tc001_exploration import (
    BUDGETS,
    CACHE_PATH,
    DATASET_PATH,
    REPO_ROOT,
    VECTOR_MANIFEST,
    Episode,
    _evidence_index,
    _repo_relative,
    build_episodes,
    flat_context,
)
from analysis.tc001b_exploration import (
    SHIPPED_CONFIG,
    dual_context,
    dual_ranked_context,
)
from analysis.tc002_exploration import TC002ExplorationError, pack_both
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256

SCHEMA = "tc002-preflight-pf4-reachability-v1"

#: The registered contrasts, named left-versus-right for the artifact only.
#: Which side wins is precisely what this module refuses to compute.
CONTRASTS = (
    ("k_first", "n_first"),
    ("k_first", "flat"),
    ("dual", "k_first"),
    ("dual_ranked", "k_first"),
)

#: Keys an artifact from this module may never carry.
_FORBIDDEN_KEYS = frozenset(
    {
        "gains",
        "losses",
        "net",
        "direction",
        "winner",
        "wins",
        "favours",
    }
)

_FORBIDDEN_SUFFIXES = ("_hits", "_only", "_wins", "_gains", "_losses")


def measure(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(VECTOR_MANIFEST.read_text(encoding="utf-8"))
    conversations = adapt_development(DATASET_PATH)

    with EmbeddingCache(
        CACHE_PATH,
        mode="reuse",
        expected_file_sha256=manifest["cache"]["file_sha256"],
        expected_content_sha256=manifest["cache"]["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {
            text: np.asarray(cache(text), dtype=np.float32)
            for case in conversations
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        }
        reuse = cache.record()
    if reuse["misses"]:
        raise TC002ExplorationError(
            "Read-only cache miss; this must cost no model calls"
        )

    by_conversation = {
        case.sample_id: build_episodes(case, vectors) for case in conversations
    }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PREFLIGHT_PF4_ONLY",
        "note": (
            "Discordant counts only. The direction of disagreement is not "
            "computed here and must not be, until the bars are committed."
        ),
        "contrasts": ["_vs_".join(pair) for pair in CONTRASTS],
        "inputs": {
            "cache_file_sha256": manifest["cache"]["file_sha256"],
            "cache_content_sha256": manifest["cache"]["content_sha256"],
            "dataset_sha256": manifest["dataset_sha256"],
            "cache_misses": reuse["misses"],
            "sources": {
                _repo_relative(path): sha256_file(path)
                for path in (
                    Path(__file__).resolve(),
                    REPO_ROOT / "src" / "analysis" / "tc002_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "tc001b_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "tc001_exploration.py",
                    REPO_ROOT / "src" / "analysis" / "ec002_k_first_packing.py",
                )
            },
        },
        "budgets": {},
    }
    for budget in BUDGETS:
        result["budgets"][str(budget)] = _reachability(
            conversations, by_conversation, vectors, budget
        )
    _forbid_direction(result)

    path = output_dir / "tc002_preflight_pf4_reachability.json"
    path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _reachability(
    conversations: Sequence[ConversationCase],
    by_conversation: dict[str, tuple[Episode, ...]],
    vectors: dict[str, np.ndarray],
    budget: int,
) -> dict[str, Any]:
    endpoints = ("any_evidence", "complete_evidence")
    discordant = {
        "_vs_".join(pair): {name: 0 for name in endpoints} for pair in CONTRASTS
    }
    concordant = {
        "_vs_".join(pair): {name: 0 for name in endpoints} for pair in CONTRASTS
    }
    evaluable = 0
    identical_delivery = 0

    for case in conversations:
        episodes = by_conversation[case.sample_id]
        records = [episode.record for episode in episodes]
        evidence = _evidence_index(case, episodes)
        for question in case.questions:
            if question.duplicate_ordinal or not question.resolved_evidence_ids:
                continue
            evaluable += 1
            target = evidence[question.identity]
            query = vectors[question.question]

            shipped = pack_both(records, query, budget, SHIPPED_CONFIG)
            _payload, flat_ids = flat_context(episodes, query, budget)
            _payload, dual_ids, _report = dual_context(episodes, query, budget)
            _payload, ranked_ids, _counts = dual_ranked_context(
                episodes, query, budget
            )
            sets = {
                "flat": set(flat_ids),
                "n_first": set(shipped["n_first"]["delivered"]),
                "k_first": set(shipped["k_first"]["delivered"]),
                "dual": set(dual_ids),
                "dual_ranked": set(ranked_ids),
            }
            if sets["n_first"] == sets["k_first"]:
                identical_delivery += 1
            outcomes = {
                arm: {
                    "any_evidence": bool(target & delivered),
                    "complete_evidence": target <= delivered,
                }
                for arm, delivered in sets.items()
            }
            for pair in CONTRASTS:
                key = "_vs_".join(pair)
                left, right = pair
                for name in endpoints:
                    if outcomes[left][name] != outcomes[right][name]:
                        discordant[key][name] += 1
                    else:
                        concordant[key][name] += 1

    rows: dict[str, dict[str, Any]] = {}
    for pair in CONTRASTS:
        key = "_vs_".join(pair)
        rows[key] = {}
        for name in endpoints:
            count = discordant[key][name]
            rows[key][name] = {
                "discordant_pairs": count,
                "concordant_pairs": concordant[key][name],
                "smallest_one_sided_exact_p_at_this_n": (
                    _one_sided_extreme_p(count) if count else 1.0
                ),
            }
    return {
        "budget_chars": budget,
        "evaluable_questions": evaluable,
        "fill_order_delivers_identical_set": identical_delivery,
        "contrasts": rows,
    }


def _one_sided_extreme_p(discordant: int) -> float:
    """The best p a sign test could return at this many discordant pairs.

    If every discordant pair fell the same way, the one-sided exact binomial p
    is ``0.5 ** discordant``. A bar set below this number is unreachable by
    construction - PF4's failing precedent, stated as an arithmetic fact rather
    than an expectation.
    """
    return math.pow(0.5, discordant)


def _forbid_direction(payload: object, path: str = "") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered = str(key).lower()
            if lowered in _FORBIDDEN_KEYS or lowered.endswith(_FORBIDDEN_SUFFIXES):
                raise TC002ExplorationError(
                    f"PF4 artifact carries a directional key at {path}/{key}"
                )
            _forbid_direction(value, f"{path}/{key}")
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            _forbid_direction(value, f"{path}[{index}]")


__all__ = ["CONTRASTS", "SCHEMA", "measure"]
