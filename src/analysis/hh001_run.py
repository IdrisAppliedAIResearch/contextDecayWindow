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
Reader = Callable[[str], str]
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
        if ledger is None:
            block: MemoryBlock = arm.block(item, conversation, budget)
        else:
            with timed(ledger, "query"):
                block = arm.block(item, conversation, budget)
        if block.chars > budget and not block.detail.get("unbudgeted"):
            raise HH001RunError(
                f"{arm.name} delivered {block.chars} characters against a "
                f"{budget}-character budget"
            )
        prompt = render_reader_prompt(item.question, block.text)
        prompt_sha = digest(prompt)
        for replicate in range(replicates):
            text = read(prompt)
            answers.append(
                Answer(
                    comparison_key=item.comparison_key,
                    arm=arm.name,
                    replicate=replicate,
                    question=item.question,
                    gold=item.gold_answer,
                    answer=text,
                    prompt_sha256=prompt_sha,
                    block_sha256=block.digest,
                    block_chars=block.chars,
                    block_truncated=block.truncated,
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
