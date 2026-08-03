"""EC-001 Tier 2 prompt, scoring, and adjudication primitives.

Reference answers enter only the scoring functions in this module. Reader
context assembly accepts a rendered retrieval block, date, and question; its
signature cannot accept a reference answer or evidence annotation.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Mapping, Sequence


NO_ANSWER = "NO_ANSWER"
MASK_SEED = "ec001-tier2-mask-v1"
H5_SEED = "sia-h5-2026-07-26-v1"
REASONING_TAG = re.compile(
    r"<(?P<closing>/)?(?P<tag>think|analysis|reasoning)\b[^>]*>",
    re.IGNORECASE,
)


class EC001Tier2Error(RuntimeError):
    """A fail-closed Tier 2 protocol gate."""


@dataclass(frozen=True)
class ScoreableResponse:
    raw_text: str
    scoreable_text: str
    reasoning_blocks_balanced: bool
    no_answer: bool
    completeness_status: str


def prepare_reader_prompt(
    delivered_block: str,
    question_date: str,
    question: str,
) -> str:
    """Apply LongMemEval's non-CoT reader prompt to an episodic block."""

    if not delivered_block.strip():
        raise EC001Tier2Error("Reader prompt requires a delivered block")
    if not question_date.strip() or not question.strip():
        raise EC001Tier2Error("Reader prompt requires date and question")
    return (
        "I will give you several history chats between you and a user. "
        "Please answer the question based on the relevant chat history."
        "\n\n\nHistory Chats:\n\n"
        f"{delivered_block}"
        f"\n\nCurrent Date: {question_date}"
        f"\nQuestion: {question}"
        "\nAnswer:"
    )


def reduce_scoreable_response(raw_text: str) -> ScoreableResponse:
    """Remove reasoning blocks and fail closed on unbalanced markup."""

    if not isinstance(raw_text, str):
        raise EC001Tier2Error("Reader response must be text")
    pieces: list[str] = []
    cursor = 0
    depth = 0
    balanced = True
    for match in REASONING_TAG.finditer(raw_text):
        if depth == 0:
            pieces.append(raw_text[cursor:match.start()])
        closing = bool(match.group("closing"))
        if closing:
            if depth == 0:
                balanced = False
            else:
                depth -= 1
        else:
            depth += 1
        cursor = match.end()
    if depth == 0:
        pieces.append(raw_text[cursor:])
    else:
        balanced = False

    scoreable = "".join(pieces).strip()
    if not balanced:
        return ScoreableResponse(
            raw_text=raw_text,
            scoreable_text=scoreable,
            reasoning_blocks_balanced=False,
            no_answer=not bool(scoreable),
            completeness_status="TRUNCATED_UNBALANCED_REASONING",
        )
    return ScoreableResponse(
        raw_text=raw_text,
        scoreable_text=scoreable,
        reasoning_blocks_balanced=True,
        no_answer=not bool(scoreable),
        completeness_status="COMPLETE",
    )


def build_label_prompt(
    question_type: str,
    question: str,
    reference_answer: str,
    scoreable_response: str,
    *,
    abstention: bool,
) -> str:
    """Return the pinned LongMemEval evaluator prompt without modification."""

    if abstention:
        template = (
            "I will give you an unanswerable question, an explanation, and a "
            "response from a model. Please answer yes if the model correctly "
            "identifies the question as unanswerable. The model could say "
            "that the information is incomplete, or some other information "
            "is given but the asked information is not.\n\nQuestion: {}"
            "\n\nExplanation: {}\n\nModel Response: {}\n\nDoes the model "
            "correctly identify the question as unanswerable? Answer yes or "
            "no only."
        )
        return template.format(question, reference_answer, scoreable_response)

    ordinary = {
        "single-session-user",
        "single-session-assistant",
        "multi-session",
    }
    if question_type in ordinary:
        template = (
            "I will give you a question, a correct answer, and a response "
            "from a model. Please answer yes if the response contains the "
            "correct answer. Otherwise, answer no. If the response is "
            "equivalent to the correct answer or contains all the "
            "intermediate steps to get the correct answer, you should also "
            "answer yes. If the response only contains a subset of the "
            "information required by the answer, answer no. \n\nQuestion: {}"
            "\n\nCorrect Answer: {}\n\nModel Response: {}\n\nIs the model "
            "response correct? Answer yes or no only."
        )
    elif question_type == "temporal-reasoning":
        template = (
            "I will give you a question, a correct answer, and a response "
            "from a model. Please answer yes if the response contains the "
            "correct answer. Otherwise, answer no. If the response is "
            "equivalent to the correct answer or contains all the "
            "intermediate steps to get the correct answer, you should also "
            "answer yes. If the response only contains a subset of the "
            "information required by the answer, answer no. In addition, do "
            "not penalize off-by-one errors for the number of days. If the "
            "question asks for the number of days/weeks/months, etc., and the "
            "model makes off-by-one errors (e.g., predicting 19 days when the "
            "answer is 18), the model's response is still correct. "
            "\n\nQuestion: {}\n\nCorrect Answer: {}\n\nModel Response: {}"
            "\n\nIs the model response correct? Answer yes or no only."
        )
    elif question_type == "knowledge-update":
        template = (
            "I will give you a question, a correct answer, and a response "
            "from a model. Please answer yes if the response contains the "
            "correct answer. Otherwise, answer no. If the response contains "
            "some previous information along with an updated answer, the "
            "response should be considered as correct as long as the updated "
            "answer is the required answer.\n\nQuestion: {}\n\nCorrect "
            "Answer: {}\n\nModel Response: {}\n\nIs the model response "
            "correct? Answer yes or no only."
        )
    elif question_type == "single-session-preference":
        template = (
            "I will give you a question, a rubric for desired personalized "
            "response, and a response from a model. Please answer yes if the "
            "response satisfies the desired response. Otherwise, answer no. "
            "The model does not need to reflect all the points in the rubric. "
            "The response is correct as long as it recalls and utilizes the "
            "user's personal information correctly.\n\nQuestion: {}"
            "\n\nRubric: {}\n\nModel Response: {}\n\nIs the model response "
            "correct? Answer yes or no only."
        )
    else:
        raise EC001Tier2Error(
            f"Unsupported LongMemEval question type: {question_type}"
        )
    return template.format(question, reference_answer, scoreable_response)


def parse_binary_label(response: str) -> bool:
    """Accept only the yes/no-only surface required by the benchmark."""

    match = re.fullmatch(r"\s*(yes|no)\s*[.!]?\s*", response, re.IGNORECASE)
    if match is None:
        raise EC001Tier2Error(
            f"Rater returned a non-binary label surface: {response!r}"
        )
    return match.group(1).casefold() == "yes"


def build_rationale_prompt(
    label_prompt: str,
    label: bool,
) -> str:
    """Request a rationale without permitting the locked label to change."""

    return (
        f"{label_prompt}\n\nThe locked yes/no decision is "
        f"{'yes' if label else 'no'}. Explain that decision in one concise, "
        "answer-grounded sentence. Do not revise the locked decision and do "
        "not mention model identity."
    )


def masked_id(question_id: str) -> str:
    digest = hashlib.sha256(
        f"{MASK_SEED}\0{question_id}".encode("utf-8")
    ).hexdigest()
    return f"EC1-{digest[:16]}"


def shuffled_ids(question_ids: Sequence[str], family_id: str) -> list[str]:
    """Return a deterministic, family-specific blind item order."""

    if len(set(question_ids)) != len(question_ids):
        raise EC001Tier2Error("Cannot shuffle duplicate question ids")
    return sorted(
        question_ids,
        key=lambda question_id: (
            hashlib.sha256(
                f"{family_id}\0{masked_id(question_id)}".encode("utf-8")
            ).hexdigest(),
            question_id,
        ),
    )


def select_h5(
    unanimous_masked_ids: Sequence[str],
    *,
    rate: float = 0.10,
    seed: str = H5_SEED,
) -> tuple[str, ...]:
    """Select an exact ceiling-sized deterministic control sample."""

    unique = sorted(set(unanimous_masked_ids))
    if len(unique) != len(unanimous_masked_ids):
        raise EC001Tier2Error("H5 population contains duplicate masked ids")
    if not 0 < rate <= 1:
        raise EC001Tier2Error("H5 rate must be in (0, 1]")
    if not unique:
        return ()
    count = max(1, math.ceil(len(unique) * rate))
    ranked = sorted(
        unique,
        key=lambda item_id: (
            hashlib.sha256(
                f"{seed}\0{item_id}".encode("utf-8")
            ).hexdigest(),
            item_id,
        ),
    )
    return tuple(ranked[:count])


def calibration_cases() -> tuple[dict, ...]:
    """Synthetic cases every family must pass before real scoring."""

    reasoning_only = reduce_scoreable_response(
        "<think>The reference answer is blue and this is substantive "
        "reasoning, but it is not final content.</think>"
    )
    if not reasoning_only.no_answer:
        raise EC001Tier2Error("Reasoning-only calibration did not reduce")
    return (
        {
            "calibration_id": "exact-positive",
            "question_type": "single-session-user",
            "question": "What color did I choose?",
            "reference_answer": "blue",
            "response": "You chose blue.",
            "abstention": False,
            "expected_label": True,
            "mechanical_no_answer": False,
        },
        {
            "calibration_id": "partial-negative",
            "question_type": "multi-session",
            "question": "Name both instruments I own.",
            "reference_answer": "a piano and a guitar",
            "response": "You own a piano.",
            "abstention": False,
            "expected_label": False,
            "mechanical_no_answer": False,
        },
        {
            "calibration_id": "reasoning-only-no-answer",
            "question_type": "single-session-user",
            "question": "What color did I choose?",
            "reference_answer": "blue",
            "response": NO_ANSWER,
            "abstention": False,
            "expected_label": False,
            "mechanical_no_answer": True,
        },
        {
            "calibration_id": "abstention-positive",
            "question_type": "single-session-user",
            "question": "What is my passport number?",
            "reference_answer": "The history does not provide it.",
            "response": "I don't know; that information is not in the history.",
            "abstention": True,
            "expected_label": True,
            "mechanical_no_answer": False,
        },
    )


def aggregate_labels(
    rows: Sequence[Mapping[str, object]],
    population_counts: Mapping[str, int],
) -> dict:
    """Aggregate binary labels without hiding the equal-quota design."""

    by_stratum: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        stratum = str(row["stratum"])
        label = row.get("label")
        if not isinstance(label, bool):
            raise EC001Tier2Error(f"Non-binary final label in {stratum}")
        by_stratum[stratum].append(label)
    if set(by_stratum) != set(population_counts):
        raise EC001Tier2Error("Scored strata differ from population weights")

    per_stratum = {
        stratum: {
            "correct": sum(values),
            "denominator": len(values),
            "accuracy": sum(values) / len(values),
        }
        for stratum, values in sorted(by_stratum.items())
    }
    total = sum(len(values) for values in by_stratum.values())
    total_correct = sum(sum(values) for values in by_stratum.values())
    population_total = sum(int(value) for value in population_counts.values())
    weighted = sum(
        per_stratum[stratum]["accuracy"] * int(population_counts[stratum])
        for stratum in population_counts
    ) / population_total
    return {
        "question_count": total,
        "raw_subset_micro_average": {
            "correct": total_correct,
            "denominator": total,
            "accuracy": total_correct / total,
            "comparability": "NON_BENCHMARK_DISTRIBUTED_EQUAL_QUOTAS",
        },
        "benchmark_population_post_stratified_accuracy": weighted,
        "benchmark_population_counts": {
            key: int(value) for key, value in population_counts.items()
        },
        "per_stratum": per_stratum,
        "observed_stratum_counts": dict(
            sorted(Counter(str(row["stratum"]) for row in rows).items())
        ),
    }
