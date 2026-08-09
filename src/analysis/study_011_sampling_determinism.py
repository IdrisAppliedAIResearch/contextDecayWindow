"""Amendment 001 Phase 1: the sampling-mode determinism probe.

Study 011's determinism spot-check established that the standing runtime
returns different answers to a byte-identical prompt at a fixed seed. It
did not establish *why*, and the amendment's §3.1 names a hypothesis:
stochastic sampling is the amplifier. Temp 1 with top-p 0.95 and top-k 20
samples from a distribution, and GPU reduction order is non-associative,
so logits can differ in their low bits between runs. Under sampling a
low-bit difference can move the sampled token; under greedy decoding it
almost never moves the argmax.

This module measures that. It does not adopt anything: §3.3 forbids Phase
1 from changing the standing runtime, and Phase 2 runs at temp 1 whatever
Phase 1 finds.

Three conditions, each over the same committed prompt set:

``standing_temp1_same_process``
    The standing runtime, ten generations per prompt in one server
    process. This is the condition the whole record was produced under.

``greedy_temp0_same_process``
    Temp 0, everything else identical, ten generations per prompt in one
    server process. Within-process reproducibility under greedy decoding.

``greedy_temp0_fresh_process``
    Temp 0, one generation per prompt per freshly started server process,
    ten processes. Across-process reproducibility under greedy decoding.

Keeping the last two apart is the point, and it is §3.2.4's requirement:
a run that reproduces inside one process and not across processes is a
different finding from one that reproduces in neither, and only the pair
separates them. §5's surrogate audit names the trap this avoids —
"temp 0 reproduces" can pass for an unrelated reason if only one of the
two is measured.

Nothing here decides anything. The probe reports identity rates and
divergence positions; §4.3's decision rule belongs to Phase 2.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"

#: The committed windows the prompt set is drawn from. Arm D is the
#: deployed configuration and the reference arm for every registered
#: contrast in Study 011, which is also why Phase 2 replicates it.
PROMPT_SOURCE = (
    STUDY_ROOT
    / "runs"
    / "study_011_live_d"
    / "context_matched_stm"
    / "constructed_prompts"
)

PROMPT_COUNT = 20
REPEATS = 10

CONDITIONS = (
    "standing_temp1_same_process",
    "greedy_temp0_same_process",
    "greedy_temp0_fresh_process",
)


class ProbeError(RuntimeError):
    """Raised when the probe cannot be run or read as specified."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


@dataclass(frozen=True)
class Prompt:
    """One committed window, addressed by the turn that produced it."""

    turn: int
    text: str
    sha256: str
    characters: int

    def as_record(self) -> dict:
        return {
            "turn": self.turn,
            "sha256": self.sha256,
            "characters": self.characters,
        }


@dataclass
class PromptOutcome:
    """The repeats for one prompt under one condition."""

    turn: int
    outputs: list[str] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return len(set(self.outputs)) <= 1

    @property
    def distinct_outputs(self) -> int:
        return len(set(self.outputs))

    def first_divergence(self) -> int | None:
        """The earliest character at which any repeat leaves the first.

        Reported against the first generation rather than pairwise across
        all of them, because the question §3.2 asks is where a rerun
        stops matching the run it is a rerun of.
        """
        if not self.outputs:
            raise ProbeError("no outputs recorded")
        positions = [
            position
            for other in self.outputs[1:]
            if (position := first_divergence(self.outputs[0], other)) is not None
        ]
        return min(positions) if positions else None

    def as_record(self) -> dict:
        return {
            "turn": self.turn,
            "generations": len(self.outputs),
            "identical": self.identical,
            "distinct_outputs": self.distinct_outputs,
            "first_divergence_char": self.first_divergence(),
            "output_lengths": [len(output) for output in self.outputs],
            "output_sha256": [_sha256(output) for output in self.outputs],
        }


def first_divergence(left: str, right: str) -> int | None:
    """Index of the first differing character, or ``None`` if identical.

    A string that is a strict prefix of the other diverges at the length
    of the shorter one: stopping earlier is a difference, not a match.
    """
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            return index
    if len(left) == len(right):
        return None
    return min(len(left), len(right))


def select_prompts(
    source: Path = PROMPT_SOURCE,
    count: int = PROMPT_COUNT,
) -> list[Prompt]:
    """Draw ``count`` committed windows, evenly spaced across the run.

    The rule is fixed here rather than chosen per invocation so the set
    is a property of the code and not of the operator. Even spacing is
    the point: window length grows from 757 characters at turn 1 to
    roughly 32,000 by the end, and a probe drawn only from late turns
    would measure one prompt length.
    """
    if count < 2:
        raise ProbeError("the prompt set must hold at least two prompts")
    files = sorted(source.glob("turn_*.txt"))
    if not files:
        raise ProbeError(f"no committed prompts under {source}")
    if len(files) < count:
        raise ProbeError(
            f"{len(files)} committed prompts available, {count} requested"
        )
    last = len(files) - 1
    indices = sorted({round(step * last / (count - 1)) for step in range(count)})
    prompts = []
    for index in indices:
        path = files[index]
        text = path.read_text(encoding="utf-8")
        prompts.append(
            Prompt(
                turn=int(path.stem.split("_")[1]),
                text=text,
                sha256=_sha256(text),
                characters=len(text),
            )
        )
    return prompts


def run_condition(
    prompts: Sequence[Prompt],
    complete: Callable[[str], str],
    repeats: int = REPEATS,
    on_round: Callable[[int], None] | None = None,
) -> list[PromptOutcome]:
    """Generate ``repeats`` completions for every prompt.

    Round-major rather than prompt-major: every prompt is generated once,
    then again, and so on. Under ``greedy_temp0_fresh_process`` a round
    is a server process, so this ordering is what makes one round mean
    one process. It also keeps the three conditions comparable, since
    prompt-major ordering would give a prompt's ten repeats a warmer
    prefix cache than round-major does.
    """
    outcomes = {prompt.turn: PromptOutcome(turn=prompt.turn) for prompt in prompts}
    for round_index in range(repeats):
        if on_round is not None:
            on_round(round_index)
        for prompt in prompts:
            outcomes[prompt.turn].outputs.append(complete(prompt.text))
    return [outcomes[prompt.turn] for prompt in prompts]


def summarize_condition(
    condition: str,
    outcomes: Sequence[PromptOutcome],
) -> dict:
    """Identity rate and divergence positions for one condition."""

    if condition not in CONDITIONS:
        raise ProbeError(f"unregistered condition: {condition}")
    if not outcomes:
        raise ProbeError("no outcomes to summarize")

    identical = [outcome for outcome in outcomes if outcome.identical]
    divergences = [
        position
        for outcome in outcomes
        if (position := outcome.first_divergence()) is not None
    ]
    distinct = [outcome.distinct_outputs for outcome in outcomes]
    return {
        "condition": condition,
        "prompts": len(outcomes),
        "generations_per_prompt": len(outcomes[0].outputs),
        "prompts_reproducing": len(identical),
        "identity_rate": round(len(identical) / len(outcomes), 4),
        "first_divergence_char": {
            "count": len(divergences),
            "min": min(divergences) if divergences else None,
            "median": _median(divergences) if divergences else None,
            "max": max(divergences) if divergences else None,
            "at_or_before_char_100": sum(1 for p in divergences if p <= 100),
            "histogram_by_decade": _decade_histogram(divergences),
        },
        "distinct_outputs_per_prompt": {
            "min": min(distinct),
            "max": max(distinct),
            "mean": round(sum(distinct) / len(distinct), 4),
        },
        "per_prompt": [outcome.as_record() for outcome in outcomes],
    }


def _median(values: Iterable[int]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def _decade_histogram(values: Iterable[int]) -> dict[str, int]:
    """Bucket divergence positions by order of magnitude.

    Divergence positions span characters 0 to thousands, so a linear
    histogram would put everything in one bucket. The distinction that
    matters is between a run that diverges on its first token and one
    that tracks for a paragraph before splitting.
    """
    counter: Counter[str] = Counter()
    for value in values:
        if value < 10:
            counter["0-9"] += 1
        elif value < 100:
            counter["10-99"] += 1
        elif value < 1000:
            counter["100-999"] += 1
        else:
            counter["1000+"] += 1
    return dict(sorted(counter.items()))


def locate_divergence(
    within_process: dict | None,
    across_process: dict | None,
) -> str:
    """Say whether greedy divergence is within-process, across, or both.

    §3.2 asks for this explicitly and §5's surrogate audit is why: a
    single greedy condition that reproduces certifies nothing, because it
    can reproduce for a reason that has nothing to do with the argmax
    being stable. Two conditions can be told apart.
    """
    if within_process is None or across_process is None:
        return "not determined: both greedy conditions are required"
    inside = within_process["identity_rate"] < 1.0
    across = across_process["identity_rate"] < 1.0
    if inside and across:
        return "both"
    if inside:
        return "within-process only"
    if across:
        return "across-process only"
    return "neither: greedy decoding reproduced in both conditions"


def build_report(
    prompts: Sequence[Prompt],
    conditions: dict[str, dict],
    runtime: dict,
) -> dict:
    """Assemble the Phase 1 artifact.

    §3.3 is restated in the artifact rather than left in the amendment,
    because the artifact is what a later reader will find first.
    """
    missing = [name for name in CONDITIONS if name not in conditions]
    within = conditions.get("greedy_temp0_same_process")
    across = conditions.get("greedy_temp0_fresh_process")
    standing = conditions.get("standing_temp1_same_process")
    hypothesis = None
    if standing is not None and within is not None and across is not None:
        sampling_diverges = standing["identity_rate"] < 1.0
        greedy_reproduces = (
            within["identity_rate"] == 1.0 and across["identity_rate"] == 1.0
        )
        if sampling_diverges and greedy_reproduces:
            hypothesis = "SUPPORTED"
        elif sampling_diverges and not greedy_reproduces:
            hypothesis = "NOT SUPPORTED: greedy decoding does not reproduce either"
        elif not sampling_diverges:
            hypothesis = (
                "NOT TESTED: the standing runtime reproduced on this prompt "
                "set, so there is no divergence for greedy decoding to remove"
            )
    return {
        "study": "011",
        "amendment": (
            "experiments/study_011/amendments/"
            "AMENDMENT_001_determinism_and_noise_band.md"
        ),
        "phase": "1",
        "title": "sampling-mode determinism probe",
        "status": "COMPLETE" if not missing else "INCOMPLETE",
        "missing_conditions": missing,
        "prompt_source": _repo_relative(PROMPT_SOURCE),
        "prompt_set": [prompt.as_record() for prompt in prompts],
        "prompt_selection_rule": (
            "Committed Arm D windows, evenly spaced across the run by index, "
            "fixed in code rather than chosen per invocation. Window length "
            "runs from 757 characters at turn 1 to about 32,000 at the end, "
            "so a set drawn from late turns alone would measure one length."
        ),
        "runtime": runtime,
        "conditions": {name: conditions[name] for name in conditions},
        "greedy_divergence_located": locate_divergence(within, across),
        "sampling_amplifier_hypothesis": hypothesis,
        "what_this_does_not_authorize": (
            "Phase 1 does not change the standing runtime (§3.3). Temp 0 is a "
            "different runtime and would break comparability with every prior "
            "study. If greedy reproduces, that is a finding about what future "
            "studies could adopt, registered separately, with the "
            "comparability cost stated. Phase 2 runs at temp 1 regardless."
        ),
        "limitation": (
            "One prompt set, one corpus, one machine. Identity rates are "
            "properties of this hardware and this llama.cpp build, not of "
            "sampling in general. The same-process conditions run against a "
            "warm prefix cache, which is what the live runs did and is "
            "therefore what is being characterized, not a confound removed."
        ),
    }


def write_report(report: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output
