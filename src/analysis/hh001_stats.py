"""Paired statistics for the A2-versus-A3 contrast.

The statistic family is NF-004's: paired discordant counts and an exact
binomial sign test. Nothing here is new, and that is deliberate — a development
run that invents its own statistic cannot hand a discordance rate forward to the
confirmatory registration's power calculation.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb
from typing import Mapping, Sequence

from analysis.hh001_endpoints import ItemOutcome


class HH001StatsError(RuntimeError):
    pass


@dataclass(frozen=True)
class PairedResult:
    treatment: str
    control: str
    endpoint: str
    n: int
    gains: int
    losses: int
    ties: int
    treatment_total: int
    control_total: int

    @property
    def net(self) -> int:
        return self.gains - self.losses

    @property
    def discordant(self) -> int:
        return self.gains + self.losses

    @property
    def discordance_rate(self) -> float:
        """The number the confirmatory registration's power calculation needs."""
        return self.discordant / self.n if self.n else 0.0

    @property
    def ratio(self) -> float | None:
        if self.losses == 0:
            return None if self.gains == 0 else float("inf")
        return self.gains / self.losses

    @property
    def accuracy_delta(self) -> float:
        return (self.treatment_total - self.control_total) / self.n if self.n else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "treatment": self.treatment,
            "control": self.control,
            "endpoint": self.endpoint,
            "n": self.n,
            "gains": self.gains,
            "losses": self.losses,
            "ties": self.ties,
            "net": self.net,
            "discordant": self.discordant,
            "discordance_rate": self.discordance_rate,
            "ratio": self.ratio,
            "treatment_total": self.treatment_total,
            "control_total": self.control_total,
            "accuracy_delta": self.accuracy_delta,
            "p_one_sided": exact_sign_test(self.gains, self.losses),
            "p_two_sided": exact_sign_test_two_sided(self.gains, self.losses),
        }


def _value(outcome: ItemOutcome, endpoint: str) -> bool:
    if endpoint == "judged":
        return outcome.judged_correct
    if endpoint == "contained":
        return outcome.contained
    raise HH001StatsError(f"Unknown endpoint {endpoint!r}")


def paired(
    treatment: Mapping[str, ItemOutcome],
    control: Mapping[str, ItemOutcome],
    *,
    treatment_name: str,
    control_name: str,
    endpoint: str = "judged",
) -> PairedResult:
    """Pair by comparison key, never by position.

    A positional pairing would silently misalign the moment one arm skips an
    item, and the misalignment would read as a mechanism difference.
    """
    keys = set(treatment) & set(control)
    if not keys:
        raise HH001StatsError("No comparison keys are shared between the arms")
    missing = (set(treatment) | set(control)) - keys
    if missing:
        raise HH001StatsError(
            f"{len(missing)} comparison keys are present in only one arm; "
            "both arms must answer the same locked items"
        )
    gains = losses = ties = 0
    treatment_total = control_total = 0
    for key in keys:
        t = _value(treatment[key], endpoint)
        c = _value(control[key], endpoint)
        treatment_total += int(t)
        control_total += int(c)
        if t and not c:
            gains += 1
        elif c and not t:
            losses += 1
        else:
            ties += 1
    return PairedResult(
        treatment=treatment_name,
        control=control_name,
        endpoint=endpoint,
        n=len(keys),
        gains=gains,
        losses=losses,
        ties=ties,
        treatment_total=treatment_total,
        control_total=control_total,
    )


def exact_sign_test(gains: int, losses: int) -> float:
    """One-sided exact binomial p for the treatment being better.

    Conditional on the discordant pairs, under the null each is a fair coin.
    """
    if gains < 0 or losses < 0:
        raise HH001StatsError("Discordant counts must be non-negative")
    n = gains + losses
    if n == 0:
        return 1.0
    tail = sum(comb(n, k) for k in range(gains, n + 1))
    return tail / (2**n)


def exact_sign_test_two_sided(gains: int, losses: int) -> float:
    n = gains + losses
    if n == 0:
        return 1.0
    return min(1.0, 2.0 * min(exact_sign_test(gains, losses), exact_sign_test(losses, gains)))


def reachability(n: int, alpha: float = 0.05) -> dict[str, object]:
    """The smallest all-gain discordant count that would reach ``alpha``.

    PF4's question, asked before any number exists: can this bar be cleared at
    all at this sample size, and can it fail? DMR-001 locked a bar that was
    unreachable by construction, and the standing rule from it is reachability
    per bar, not per statistic.
    """
    if n <= 0:
        raise HH001StatsError("Sample size must be positive")
    smallest = None
    for discordant in range(1, n + 1):
        if exact_sign_test(discordant, 0) <= alpha:
            smallest = discordant
            break
    return {
        "n": n,
        "alpha": alpha,
        "smallest_all_gain_discordant_reaching_alpha": smallest,
        "reachable": smallest is not None and smallest <= n,
        "null_reachable": True,
        "reversal_reachable": True,
    }


def summarize(outcomes: Sequence[ItemOutcome], endpoint: str = "judged") -> dict[str, object]:
    if not outcomes:
        raise HH001StatsError("No outcomes to summarize")
    correct = sum(1 for outcome in outcomes if _value(outcome, endpoint))
    return {
        "endpoint": endpoint,
        "n": len(outcomes),
        "correct": correct,
        "accuracy": correct / len(outcomes),
    }


__all__ = [
    "HH001StatsError",
    "PairedResult",
    "exact_sign_test",
    "exact_sign_test_two_sided",
    "paired",
    "reachability",
    "summarize",
]
