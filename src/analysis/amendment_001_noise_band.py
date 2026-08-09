"""Amendment 001 Phase 2: the instrument's noise band.

Five replicates of Arm D, the deployed configuration, under identical
settings on the standing runtime. The question is not whether Arm D is
good. It is whether a 13-point rubric read once per arm can resolve the
differences this program has been reporting.

Three properties of this module exist because the measurement is easy to
fake:

* **The decision rule is read from a file whose digest is pinned here.**
  §4.3 must commit before any run is scored, and a rule that can be
  edited after the number is known is not a rule. If the committed file
  changes, the verdict raises rather than reports.
* **Nothing is summarized away.** §4.2 requires every individual total
  listed, the full range, per-question variability, and rater
  disagreement kept separate from run-to-run variation. A standard
  deviation from five runs is reported with its caveat attached to the
  number, not in a footnote.
* **The retrospective application is computed, not narrated.** Every
  scored gap the amendment names is compared to the band by the same
  expression, so a result the program likes and a result it does not get
  the same treatment.

The band cannot rescue anything. §1.2's non-rescue clause is carried in
the artifact this module writes.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
NOISE_BAND_ROOT = STUDY_ROOT / "noise_band"
DECISION_RULE = NOISE_BAND_ROOT / "DECISION_RULE.md"

#: The digest of the decision rule as committed, before any replicate was
#: scored (commit ``c07e1e27``). LF-normalized, because the repository is
#: checked out with CRLF on this machine and the rule is a text file, not
#: its line endings.
DECISION_RULE_SHA256 = (
    "d412f8e0f713887bf8765a4c4075458c3bc74a54560e0a26dc46761f921c8e83"
)

REPLICATES = 5
QUESTIONS = tuple(f"Q{index}" for index in range(1, 14))

#: Blind labels, assigned by response digest so the ordering carries no
#: information about which replicate ran first.
LABEL_VOCABULARY = (
    "run_alpha",
    "run_beta",
    "run_gamma",
    "run_delta",
    "run_epsilon",
    "run_zeta",
    "run_eta",
    "run_theta",
)

#: Every scored gap §2 of the amendment names, with the reading each
#: currently carries. The band is applied to all four by one expression.
RECORDED_GAPS = (
    {
        "result": "Study 009 same-seed contrast, S vs L",
        "gap": 3.0,
        "currently_reads_as": "the arc's clean architectural number",
        "artifact": "experiments/study_009/study_009_report.md",
    },
    {
        "result": "LV-001 targeted regression",
        "gap": -2.0,
        "currently_reads_as": "the kill that un-promoted A3",
        "artifact": "experiments/components/live_validation/",
    },
    {
        "result": "Study 011 B1, C vs D",
        "gap": -1.0,
        "currently_reads_as": "the kill in this study",
        "artifact": "experiments/study_011/evaluation/verdict.json",
    },
    {
        "result": "The corrected treatment series, 8.5 to 12.0",
        "gap": 3.5,
        "currently_reads_as": "the arc's headline improvement",
        "artifact": "ERRATA.md",
    },
)

#: Offline, deterministic results the band does not touch. Listed so the
#: artifact's scope cannot be over-read in either direction.
UNAFFECTED = (
    "gate outcomes",
    "delivery counts",
    "character accounting",
    "packing measurements",
    "EC-002's 152 gains and zero losses",
    "IC-001's zero K episodes at 8 of 8 probes",
    "Arm D's per-question identity to Arm A, with byte-identical windows "
    "at turns 117, 118 and 119",
)


class NoiseBandError(RuntimeError):
    """Raised when the band cannot be measured or read as registered."""


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def assert_decision_rule(path: Path = DECISION_RULE) -> str:
    """The rule must be the one committed before scoring, or nothing is read."""

    if not path.is_file():
        raise NoiseBandError(f"the committed decision rule is missing: {path}")
    digest = _sha256_lf(path)
    if digest != DECISION_RULE_SHA256:
        raise NoiseBandError(
            "the decision rule changed after it was committed: "
            f"{digest} != {DECISION_RULE_SHA256}. §4.3 commits before any run "
            "is scored; a rule edited afterwards is not a rule."
        )
    return digest


def seal_replicates(run_dirs: Mapping[str, Path]) -> dict:
    """Assign blind labels from response digests, never by choice.

    The same construction Study 011 §6.1 used, widened past four runs.
    Sorting by digest matters more here than it did there: the replicates
    are identical by design, so run order is the only thing a rater could
    anchor on, and digest order destroys it.
    """
    if not run_dirs:
        raise NoiseBandError("no replicates to seal")
    if len(run_dirs) > len(LABEL_VOCABULARY):
        raise NoiseBandError(
            f"{len(run_dirs)} replicates exceeds the label vocabulary"
        )
    resolved = {name: Path(directory).resolve() for name, directory in run_dirs.items()}
    if len(set(resolved.values())) != len(resolved):
        raise NoiseBandError(
            "two replicates name the same directory; that is a harness fault, "
            "not a measurement"
        )
    digests = {}
    for name, directory in resolved.items():
        responses = directory / "responses.md"
        if not responses.is_file():
            raise NoiseBandError(f"no responses file for {name}: {responses}")
        digests[name] = hashlib.sha256(responses.read_bytes()).hexdigest()
    # Byte-identical replicates from distinct directories are a result, not
    # a fault. Phase 1 found this runtime reproducing 600 of 600 generations
    # when request history was held fixed, so identical replicates are a
    # state the measurement has to be able to report. Only the same
    # directory counted twice is a harness fault, and that is checked above.
    identical = len(digests) - len(set(digests.values()))
    order = sorted(run_dirs, key=lambda name: (digests[name], name))
    mapping = {
        LABEL_VOCABULARY[index]: name for index, name in enumerate(order)
    }
    return {
        "sealed": True,
        "do_not_open": (
            "Open only after the aggregated blind scores are committed. "
            "Git history is the audit trail."
        ),
        "assignment_source": (
            "SHA-256 of each replicate's responses.md, sorted; deterministic "
            "and not selected by the rater or by anyone who has seen a score"
        ),
        "mapping": mapping,
        "response_sha256": digests,
        "byte_identical_replicate_pairs": identical,
        "byte_identical_note": (
            "Replicates with the same response digest are reported, not "
            "refused. Phase 1 found the standing runtime reproducing every "
            "generation when request history was held fixed, so identical "
            "replicates are a state this measurement must be able to report. "
            "Ties break by run id so the labelling stays deterministic."
        ),
        "combined_sha256": hashlib.sha256(
            "".join(digests[name] for name in sorted(digests)).encode("utf-8")
        ).hexdigest(),
    }


@dataclass(frozen=True)
class Band:
    """The measured spread, and nothing derived from it."""

    totals: tuple[float, ...]
    minimum: float
    maximum: float
    width: float
    standard_deviation: float

    def as_record(self) -> dict:
        return {
            "individual_totals": list(self.totals),
            "min": self.minimum,
            "max": self.maximum,
            "band": self.width,
            "standard_deviation": self.standard_deviation,
            "standard_deviation_caveat": (
                "n = 5 estimates a standard deviation poorly. The band is the "
                "range; this figure is indicative only and §4.3 does not read it."
            ),
        }


def measure_band(totals: Mapping[str, float]) -> Band:
    """max − min of the per-run totals. Nothing trimmed, nothing dropped."""

    if len(totals) < 2:
        raise NoiseBandError("a band needs at least two runs")
    values = [float(value) for value in totals.values()]
    return Band(
        totals=tuple(sorted(values)),
        minimum=min(values),
        maximum=max(values),
        width=round(max(values) - min(values), 4),
        standard_deviation=round(statistics.stdev(values), 4),
    )


def read_band(width: float) -> dict:
    """§4.3, with the boundaries the decision rule pinned.

    Inclusive at the lower edge in both directions: exactly 0.5 and
    exactly 1.5 both fall in the middle row. Pinned before the number was
    known so a band landing on a boundary cannot be read the convenient way.
    """
    if width < 0.5:
        return {
            "row": "< 0.5",
            "reading": "The instrument resolves one-point differences",
            "consequence": (
                "Committed verdicts stand as written. Study 011's -1.0 and "
                "LV-001's -2.0 are interpretable."
            ),
            "paper_action": "no revision required",
        }
    if width <= 1.5:
        return {
            "row": "0.5 - 1.5",
            "reading": (
                "One-point differences are not interpretable; three-point "
                "differences are"
            ),
            "consequence": (
                "Study 011's -1.0 and LV-001's -2.0 are re-read as NOT "
                "DEMONSTRATED. Study 009's 3.0 and the 3.5 series improvement "
                "stand."
            ),
            "paper_action": "limitations revised; no structural revision",
        }
    return {
        "row": "> 1.5",
        "reading": "Nothing below about 3 points is interpretable",
        "consequence": (
            "Most of the arc's scored verdicts are re-read as UNDETERMINED. "
            "Study 009's 3.0 is marginal."
        ),
        "paper_action": "PAPER_001.md requires a structural revision, not a caveat",
    }


def apply_uniformly(width: float, gaps: Sequence[dict] = RECORDED_GAPS) -> list[dict]:
    """Compare every recorded gap to the band by one expression.

    The expression is deliberately the same for the results the program
    would keep and the results it would lose. A gap wider than the band is
    still only *not excluded by* the band — five runs of one arm cannot
    turn a single-sample difference into a demonstrated one.
    """
    applied = []
    for row in gaps:
        magnitude = abs(float(row["gap"]))
        exceeds = magnitude > width
        applied.append(
            {
                **row,
                "magnitude": magnitude,
                "exceeds_band": exceeds,
                "re_read_as": (
                    "not excluded by the band; the original reading survives"
                    if exceeds
                    else "NOT DEMONSTRATED: the gap is inside the measured "
                    "run-to-run spread of one configuration"
                ),
            }
        )
    return applied


def per_question_variability(
    scores: Mapping[str, Mapping[str, float]],
) -> dict:
    """Which questions move across replicates, and which do not.

    §4.2.4: a band concentrated in two questions means something
    different from a band spread across all thirteen. The first says the
    instrument is unstable on two items; the second says it is unstable.
    """
    if not scores:
        raise NoiseBandError("no scores to analyse")
    rows = []
    for question in QUESTIONS:
        values = []
        for label, per_question in scores.items():
            if question not in per_question:
                raise NoiseBandError(f"{label} is missing {question}")
            values.append(float(per_question[question]))
        rows.append(
            {
                "question": question,
                "values": values,
                "distinct_values": sorted(set(values)),
                "range": round(max(values) - min(values), 4),
                "moved": len(set(values)) > 1,
            }
        )
    moved = [row for row in rows if row["moved"]]
    total_movement = round(sum(row["range"] for row in moved), 4)
    return {
        "questions_that_moved": [row["question"] for row in moved],
        "questions_that_moved_count": len(moved),
        "questions_stable_count": len(rows) - len(moved),
        "summed_per_question_range": total_movement,
        "concentration": (
            "concentrated" if len(moved) <= 3 else "spread across the rubric"
        ),
        "what_this_distinguishes": (
            "A band carried by two or three items is a statement about those "
            "items. A band spread across the rubric is a statement about the "
            "instrument. §4.2.4 requires the difference to be visible."
        ),
        "per_question": rows,
    }


def rater_disagreement(aggregated: Mapping) -> dict:
    """Rater spread, kept apart from run-to-run spread.

    §4.2.5 is explicit that these are two noise sources and must not be
    pooled. Pooling them would let same-family rater agreement look like
    instrument stability, which is exactly the direction §4.1 warns about.
    """
    per_item = aggregated.get("per_item")
    if not per_item:
        raise NoiseBandError("aggregated scores carry no per-item detail")
    by_label: dict[str, dict] = {}
    for row in per_item.values():
        bucket = by_label.setdefault(
            row["blind_label"],
            {"items": 0, "unanimous": 0, "majority": 0, "split": 0, "spread": 0.0},
        )
        bucket["items"] += 1
        bucket[row["agreement"]] += 1
        values = [float(value) for value in row["rater_values"]]
        bucket["spread"] += max(values) - min(values)
    for bucket in by_label.values():
        bucket["mean_rater_spread_per_item"] = round(
            bucket.pop("spread") / bucket["items"], 4
        )
        bucket["unanimous_rate"] = round(bucket["unanimous"] / bucket["items"], 4)
    return {
        "per_replicate": by_label,
        "this_is_not_the_band": (
            "Rater disagreement is variation in reading one answer. The band "
            "is variation in producing one. §4.2.5 keeps them apart; pooling "
            "them would let same-family agreement read as instrument stability."
        ),
        "family_departure": (
            "Three distinct models, one family. Shared-family bias inflates "
            "apparent agreement, and inflated agreement understates the band -- "
            "the direction that flatters the record. Disclosed in the decision "
            "rule before the measurement, not after it."
        ),
    }


def build_report(
    scores: Mapping[str, Mapping[str, float]],
    aggregated: Mapping,
    runs: Sequence[dict],
    decision_rule_sha256: str,
) -> dict:
    """Assemble the band verdict."""

    if len(scores) != REPLICATES:
        raise NoiseBandError(
            f"§4.1 registers N = {REPLICATES}; {len(scores)} were scored. "
            "The decision rule's last row says report and stop rather than "
            "estimate from fewer than N."
        )
    totals = {
        label: round(sum(float(value) for value in per_question.values()), 2)
        for label, per_question in scores.items()
    }
    band = measure_band(totals)
    return {
        "study": "011",
        "amendment": (
            "experiments/study_011/amendments/"
            "AMENDMENT_001_determinism_and_noise_band.md"
        ),
        "phase": "2",
        "title": "noise band on the deployed configuration",
        "design": (
            f"Arm D, the deployed configuration, repeated N = {REPLICATES}. "
            "Identical corpus, settings, seed and standing runtime, temp 1."
        ),
        "decision_rule": {
            "path": "experiments/study_011/noise_band/DECISION_RULE.md",
            "sha256_lf": decision_rule_sha256,
            "committed_before_scoring": True,
        },
        "runs": list(runs),
        "individual_totals_by_replicate": totals,
        "band": band.as_record(),
        "verdict": read_band(band.width),
        "uniform_application": apply_uniformly(band.width),
        "per_question_variability": per_question_variability(scores),
        "rater_disagreement": rater_disagreement(aggregated),
        "unaffected_by_the_band": list(UNAFFECTED),
        "non_rescue_clause": (
            "B1 fired. Arm C scored 7.0 against Arm D's 8.0 and the packing "
            "correction is not adopted. This band may not be cited in support "
            "of any adoption decision for K-first packing. Any future adoption "
            "requires a new study with its own pre-registration and its own "
            "bar. Amendment 001 §1.2, binding."
        ),
        "limitations": [
            "n = 5 on one configuration, one corpus, one seed, one machine.",
            "Five runs can cluster by chance and understate the true spread; "
            "every individual total is listed above so the clustering is visible.",
            "The band is measured on Arm D and applied to other arms by "
            "assumption. Noise may be configuration-dependent.",
            "A gap wider than the band is not thereby demonstrated. It is only "
            "not excluded by this measurement.",
            "Three raters, three distinct models, one family.",
        ],
    }


def write_report(report: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output
