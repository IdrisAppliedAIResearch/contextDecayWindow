"""Ordered execution for the HH-001 development run.

Stage order is the point of this module, not a convenience:

1. every arm's answers are generated and **sealed** before any judging;
2. the judge sees a blinded, shuffled surface with no arm labels;
3. the commitments gate runs before a contrast is computed;
4. both endpoints are computed on every answer, and a sign disagreement blocks
   any directional claim.

Nothing here contacts a model. Generation and judging are injected callables,
so the whole ordering is testable without a server.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from analysis.hh001_arms import Arm, MemoryBlock
from analysis.hh001_commitments import Commitments, verify_run
from analysis.hh001_corpus import Conversation, Item
from analysis.hh001_cost import CountingClient, Ledger, timed
from analysis.hh001_endpoints import (
    ItemOutcome,
    aggregate,
    contains_gold,
    sign_check,
    unanimity_rate,
)
from analysis.hh001_reader import ReaderReply, normalize as normalize_reply
from analysis.hh001_prompt import (
    blinded_surface,
    digest,
    parse_judge_verdict,
    render_judge_prompt,
    render_reader_prompt,
    template_manifest,
)
from analysis.hh001_stats import paired, summarize

#: ``(prompt) -> answer text``
Reader = Callable[..., Any]
#: ``(prompt) -> raw judge reply``
Judge = Callable[[str], str]


class HH001RunError(RuntimeError):
    pass


@dataclass(frozen=True)
class Answer:
    comparison_key: str
    arm: str
    replicate: int
    question: str
    gold: str
    answer: str
    prompt_sha256: str
    block_sha256: str
    block_chars: int
    block_truncated: bool
    #: Per-call cost, kept on the row rather than only in an aggregate ledger.
    #: Prompt tokens are the axis the arms differ most on: A1 sends a whole
    #: conversation, A3 sends a couple of thousand characters.
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    seconds: float = 0.0
    seed: int = -1
    answer_truncated: bool = False
    #: Blocks are built once per item and reused across replicates, so this is
    #: the memory layer's own latency, not the reader's.
    block_seconds: float = 0.0
    units_delivered: int = 0
    units_available: int = 0
    #: Does the gold answer survive *into the delivered block*? Computed with
    #: no model. A1/A2/A4 deliver stored text, so this is a selection question.
    #: A3 delivers model-written memories, so for it this merges selection with
    #: whether extraction preserved the fact at all — `store_probe` separates
    #: those two afterwards.
    gold_in_block: bool = False
    #: Does the gold answer appear anywhere in the source conversation? The
    #: denominator: an item whose answer is not stated verbatim anywhere cannot
    #: be lost by any layer, and counting it as a loss would blame the memory
    #: for the corpus.
    gold_in_source: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "comparison_key": self.comparison_key,
            "arm": self.arm,
            "replicate": self.replicate,
            "question": self.question,
            "gold": self.gold,
            "answer": self.answer,
            "prompt_sha256": self.prompt_sha256,
            "block_sha256": self.block_sha256,
            "block_chars": self.block_chars,
            "block_truncated": self.block_truncated,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_tokens": self.cached_tokens,
            "seconds": round(self.seconds, 3),
            "seed": self.seed,
            "answer_truncated": self.answer_truncated,
            "block_seconds": round(self.block_seconds, 4),
            "units_delivered": self.units_delivered,
            "units_available": self.units_available,
            "gold_in_block": self.gold_in_block,
            "gold_in_source": self.gold_in_source,
        }


def generate_arm(
    arm: Arm,
    items: Sequence[Item],
    conversations: Mapping[str, Conversation],
    *,
    reader: Reader,
    budget: int,
    replicates: int,
    ledger: Ledger | None = None,
) -> list[Answer]:
    """Run one arm over every item, ``replicates`` times.

    The replicate schedule is positional and registered: replicate ``r`` of one
    arm pairs with replicate ``r`` of another. Pairing by anything else would
    let a favourable run be chosen after the fact.
    """
    answers: list[Answer] = []
    read = reader if ledger is None else CountingClient(reader, ledger, "read")
    for item in items:
        conversation = conversations.get(item.sample_id)
        if conversation is None:
            raise HH001RunError(f"No conversation loaded for {item.sample_id}")
        block_started = time.perf_counter()
        if ledger is None:
            block: MemoryBlock = arm.block(item, conversation, budget)
        else:
            with timed(ledger, "query"):
                block = arm.block(item, conversation, budget)
        block_seconds = time.perf_counter() - block_started
        if block.chars > budget and not block.detail.get("unbudgeted"):
            raise HH001RunError(
                f"{arm.name} delivered {block.chars} characters against a "
                f"{budget}-character budget"
            )
        prompt = render_reader_prompt(item.question, block.text)
        prompt_sha = digest(prompt)
        gold_in_block = contains_gold(block.text, item.gold_answer)
        gold_in_source = contains_gold(conversation.full_text, item.gold_answer)
        for replicate in range(replicates):
            reply = normalize_reply(read(prompt, replicate))
            answers.append(
                Answer(
                    comparison_key=item.comparison_key,
                    arm=arm.name,
                    replicate=replicate,
                    question=item.question,
                    gold=item.gold_answer,
                    answer=reply.text,
                    prompt_sha256=prompt_sha,
                    block_sha256=block.digest,
                    block_chars=block.chars,
                    block_truncated=block.truncated,
                    prompt_tokens=reply.prompt_tokens,
                    completion_tokens=reply.completion_tokens,
                    cached_tokens=reply.cached_tokens,
                    seconds=reply.seconds,
                    seed=reply.seed,
                    answer_truncated=reply.truncated,
                    block_seconds=block_seconds,
                    units_delivered=block.units_delivered,
                    units_available=block.units_available,
                    gold_in_block=gold_in_block,
                    gold_in_source=gold_in_source,
                )
            )
    return answers


def seal_answers(answers: Sequence[Answer], path: Path) -> str:
    """Write every answer before anything is judged.

    ``AGENTS.md`` §4: commit every arm's scores before anyone opens mechanism
    logs; git order is the evidence. The same discipline applies one stage
    earlier here — the answers exist on disk before a judge has an opinion.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "hh001-answers-v1",
        "count": len(answers),
        "answers": [answer.as_dict() for answer in answers],
    }
    raw = (
        json.dumps(payload, ensure_ascii=True, indent=1, sort_keys=True) + "\n"
    ).encode("utf-8")
    path.write_bytes(raw)
    import hashlib

    return hashlib.sha256(raw).hexdigest()


def judge_answers(
    answers: Sequence[Answer], *, judge: Judge, seed: str = "5005"
) -> dict[str, bool]:
    """Judge a blinded, shuffled surface. Returns ``blind_id -> correct``."""
    surface, mapping = blinded_surface(
        [answer.as_dict() for answer in answers], seed=seed
    )
    verdicts: dict[str, bool] = {}
    for entry in surface:
        prompt = render_judge_prompt(entry["question"], entry["gold"], entry["answer"])
        correct, _reason = parse_judge_verdict(judge(prompt))
        verdicts[entry["blind_id"]] = correct
    if len(verdicts) != len(answers):
        raise HH001RunError("Judge did not return a verdict for every answer")
    return {
        f"{mapping[bid]['comparison_key']}\0{mapping[bid]['arm']}\0{mapping[bid]['replicate']}": value
        for bid, value in verdicts.items()
    }


def build_outcomes(
    answers: Sequence[Answer], verdicts: Mapping[str, bool]
) -> dict[str, dict[str, ItemOutcome]]:
    """Fold replicates into per-item outcomes, per arm.

    Both endpoints are computed on every answer, per plan §5. Containment is
    computed here rather than at generation time so the two endpoints see the
    identical answer string.
    """
    grouped: dict[tuple[str, str], list[Answer]] = {}
    for answer in answers:
        grouped.setdefault((answer.arm, answer.comparison_key), []).append(answer)

    outcomes: dict[str, dict[str, ItemOutcome]] = {}
    for (arm, key), rows in grouped.items():
        rows.sort(key=lambda row: row.replicate)
        judged_votes = []
        contained_votes = []
        for row in rows:
            vote_key = f"{row.comparison_key}\0{row.arm}\0{row.replicate}"
            if vote_key not in verdicts:
                raise HH001RunError(f"No judge verdict for {vote_key!r}")
            judged_votes.append(verdicts[vote_key])
            contained_votes.append(contains_gold(row.answer, row.gold))
        outcomes.setdefault(arm, {})[key] = aggregate(
            key, arm, judged_votes, contained_votes
        )
    return outcomes



def cost_summary(answers: Sequence[Answer]) -> dict[str, Any]:
    """Per-arm cost, from the answer rows.

    Reported per call rather than as a total, because the arms differ by an
    order of magnitude in prompt size and a total hides that. `block_seconds`
    is deduplicated by item: a block is built once and reused across
    replicates, so summing it across replicates would triple-count the memory
    layer's own latency.
    """
    by_arm: dict[str, dict[str, Any]] = {}
    for arm in sorted({a.arm for a in answers}):
        rows = [a for a in answers if a.arm == arm]
        prompts = sorted(a.prompt_tokens for a in rows)
        latencies = sorted(a.seconds for a in rows)
        blocks = sorted(a.block_chars for a in rows)
        seen: dict[str, float] = {}
        for row in rows:
            seen.setdefault(row.comparison_key, row.block_seconds)

        def pct(values: list[float], q: float) -> float:
            return round(values[min(len(values) - 1, int(q * len(values)))], 3)

        by_arm[arm] = {
            "calls": len(rows),
            "prompt_tokens_total": sum(a.prompt_tokens for a in rows),
            "prompt_tokens_mean": round(sum(prompts) / len(rows), 1),
            "prompt_tokens_p50": pct([float(v) for v in prompts], 0.50),
            "completion_tokens_total": sum(a.completion_tokens for a in rows),
            "reader_seconds_p50": pct(latencies, 0.50),
            "reader_seconds_p95": pct(latencies, 0.95),
            "reader_seconds_total": round(sum(latencies), 1),
            "block_chars_mean": round(sum(blocks) / len(rows), 1),
            "block_seconds_p50": pct(sorted(seen.values()), 0.50),
            "block_seconds_total": round(sum(seen.values()), 2),
            "answers_hitting_the_token_cap": sum(1 for a in rows if a.answer_truncated),
        }
    baseline = min(
        (v["prompt_tokens_total"] for v in by_arm.values() if v["prompt_tokens_total"]),
        default=0,
    )
    for value in by_arm.values():
        value["prompt_tokens_relative_to_cheapest_arm"] = (
            round(value["prompt_tokens_total"] / baseline, 2) if baseline else None
        )
    return by_arm



def fidelity_summary(answers: Sequence[Answer]) -> dict[str, Any]:
    """Does the answer survive into the delivered context, per arm?

    This is the mechanism behind any accuracy difference, and it needs no
    model. Restricted to items whose gold answer is stated verbatim somewhere
    in the source conversation, because an item the corpus never states
    plainly cannot be lost by a memory layer, and counting it would blame the
    memory for the corpus.

    For A1, A2 and A4 a miss is a **selection** failure: the text exists and
    was not chosen. For A3 a miss is selection *or* extraction — the fact may
    never have been written into a memory at all. `store_probe` separates
    those; this does not, and must not be reported as if it did.
    """
    report: dict[str, Any] = {}
    for arm in sorted({a.arm for a in answers}):
        rows = [a for a in answers if a.arm == arm]
        by_item = {}
        for row in rows:
            by_item.setdefault(row.comparison_key, row)
        eligible = [r for r in by_item.values() if r.gold_in_source]
        kept = sum(1 for r in eligible if r.gold_in_block)
        report[arm] = {
            "items": len(by_item),
            "gold_stated_in_source": len(eligible),
            "gold_survived_into_block": kept,
            "survival_rate": round(kept / len(eligible), 4) if eligible else None,
            "lost": len(eligible) - kept,
            "miss_is": (
                "selection only (the arm delivers stored text verbatim)"
                if arm != "A3_MEM0"
                else "selection or extraction; store_probe separates them"
            ),
        }
    return report


def depth_strata(
    outcomes: Mapping[str, Mapping[str, ItemOutcome]],
    items: Sequence[Item],
    endpoint: str = "judged",
) -> dict[str, Any]:
    """Accuracy by how far back the answer lives — the long-horizon axis.

    An item whose evidence sits in the first tenth of a 680-turn conversation
    is the case a memory layer exists for. Overall accuracy averages that case
    away.
    """
    edges = [(0.0, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.01)]
    depth = {i.comparison_key: i.evidence_depth for i in items}
    report: dict[str, Any] = {}
    for arm, rows in outcomes.items():
        buckets: dict[str, dict[str, int]] = {}
        for low, high in edges:
            name = f"{low:.2f}-{min(high, 1.0):.2f}"
            keys = [
                key for key in rows
                if depth.get(key) is not None and low <= depth[key] < high
            ]
            correct = sum(
                1 for key in keys
                if (rows[key].judged_correct if endpoint == "judged"
                    else rows[key].contained)
            )
            buckets[name] = {
                "n": len(keys),
                "correct": correct,
                "accuracy": round(correct / len(keys), 4) if keys else None,
            }
        report[arm] = buckets
    return {
        "endpoint": endpoint,
        "bucket": "fraction of the conversation before the earliest evidence turn",
        "by_arm": dict(sorted(report.items())),
    }


def analyze(
    outcomes: Mapping[str, Mapping[str, ItemOutcome]],
    commitments: Commitments,
    *,
    ledgers: Mapping[str, Ledger] | None = None,
) -> dict[str, Any]:
    """Compute the contrast under both endpoints and apply the sign guard."""
    treatment_name, control_name = commitments.contrast
    for name in (treatment_name, control_name):
        if name not in outcomes:
            raise HH001RunError(f"Contrast arm {name!r} produced no outcomes")

    judged = paired(
        outcomes[treatment_name],
        outcomes[control_name],
        treatment_name=treatment_name,
        control_name=control_name,
        endpoint="judged",
    )
    contained = paired(
        outcomes[treatment_name],
        outcomes[control_name],
        treatment_name=treatment_name,
        control_name=control_name,
        endpoint="contained",
    )
    check = sign_check(judged.net, contained.net)

    per_arm: dict[str, Any] = {}
    for arm, rows in outcomes.items():
        values = list(rows.values())
        per_arm[arm] = {
            "judged": summarize(values, "judged"),
            "contained": summarize(values, "contained"),
            "judged_unanimity_rate": unanimity_rate(values, "judged"),
            "contained_unanimity_rate": unanimity_rate(values, "contained"),
            "cost": ledgers[arm].as_dict() if ledgers and arm in ledgers else None,
        }

    return {
        "schema": "hh001-development-result-v1",
        "commitments_sha256": commitments.digest,
        "replicates": commitments.replicates,
        "below_confirmatory_replicates": commitments.below_confirmatory_replicates,
        "contrast": {
            "judged": judged.as_dict(),
            "contained": contained.as_dict(),
        },
        "sign_check": {
            "judged_net": check.judged_net,
            "contained_net": check.contained_net,
            "agree": check.agree,
            "reason": check.reason,
            "blocks_directional_claim": check.blocks_directional_claim,
        },
        "directional_claim_permitted": check.agree,
        "per_arm": dict(sorted(per_arm.items())),
        "standing": "DEVELOPMENT — not confirmatory, and never becomes so",
        "substrate": "local; no comparison to any published Mem0 number is licensed",
    }


def run(
    arms: Sequence[Arm],
    items: Sequence[Item],
    conversations: Mapping[str, Conversation],
    commitments: Commitments,
    *,
    reader: Reader,
    judge: Judge,
    outcome_dir: Path,
    ledgers: Mapping[str, Ledger] | None = None,
) -> dict[str, Any]:
    """Generate, seal, judge, gate, then analyze — in that order."""
    if len(items) != commitments.subsample_size:
        raise HH001RunError(
            f"{len(items)} items supplied against a committed "
            f"{commitments.subsample_size}"
        )
    all_answers: list[Answer] = []
    seals: dict[str, str] = {}
    for arm in arms:
        answers = generate_arm(
            arm,
            items,
            conversations,
            reader=reader,
            budget=commitments.budget_chars,
            replicates=commitments.replicates,
            ledger=ledgers.get(arm.name) if ledgers else None,
        )
        seals[arm.name] = seal_answers(answers, outcome_dir / f"{arm.name}.json")
        all_answers.extend(answers)

    verify_run(
        commitments,
        arms_run=tuple(arm.name for arm in arms),
        budget_chars=commitments.budget_chars,
        items_scored=len(items),
        replicates=commitments.replicates,
        template_manifest=template_manifest().as_dict(),
    )

    verdicts = judge_answers(all_answers, judge=judge, seed=commitments.seed)
    outcomes = build_outcomes(all_answers, verdicts)
    result = analyze(outcomes, commitments, ledgers=ledgers)
    result["answer_seals"] = dict(sorted(seals.items()))
    result["cost"] = cost_summary(all_answers)
    result["fidelity"] = fidelity_summary(all_answers)
    result["long_horizon"] = depth_strata(outcomes, items)
    result["long_horizon_contained"] = depth_strata(outcomes, items, "contained")
    return result


__all__ = [
    "Answer",
    "HH001RunError",
    "Judge",
    "Reader",
    "analyze",
    "build_outcomes",
    "generate_arm",
    "judge_answers",
    "run",
    "seal_answers",
]
