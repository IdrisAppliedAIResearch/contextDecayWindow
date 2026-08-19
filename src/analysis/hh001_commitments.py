"""The six pre-commitments, and the gate that holds the run to them.

``HH_001_DEVELOPMENT_PLAN.md`` §6 is deliberately short. Its only job is to stop
us getting a number and then deciding what it meant. This module makes that
mechanical: the commitments are written and hashed before the first generation
call, and the runner refuses to produce a result that does not match them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PLAN = Path("experiments/comparisons/hh_001/HH_001_DEVELOPMENT_PLAN.md")

#: Confirmatory minimum, carried from Study 011 Amendment 001. Development runs
#: below it deliberately and says so (plan §8).
CONFIRMATORY_MIN_REPLICATES = 5


class HH001CommitmentError(RuntimeError):
    pass


@dataclass(frozen=True)
class Commitments:
    """Everything fixed before the first generation call."""

    arms: tuple[str, ...]
    primary_endpoint: str
    cross_check_endpoint: str
    budget_chars: int
    subsample_size: int
    replicates: int
    contrast: tuple[str, str]
    seed: str = "5005"
    population: str = "answerable"
    plan_sha256: str = ""
    template_manifest: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(set(self.arms)) != len(self.arms):
            raise HH001CommitmentError("Duplicate arm in the commitments")
        if self.replicates < 1:
            raise HH001CommitmentError("Replicates must be at least 1")
        if self.replicates % 2 == 0:
            raise HH001CommitmentError(
                "Replicates must be odd so the per-item majority cannot tie"
            )
        if self.budget_chars <= 0:
            raise HH001CommitmentError("Budget must be positive")
        if self.subsample_size <= 0:
            raise HH001CommitmentError("Subsample size must be positive")
        if self.primary_endpoint == self.cross_check_endpoint:
            raise HH001CommitmentError(
                "The cross-check must be a different endpoint from the primary"
            )
        for name in self.contrast:
            if name not in self.arms:
                raise HH001CommitmentError(
                    f"Contrast names {name!r}, which is not a committed arm"
                )
        if self.contrast[0] == self.contrast[1]:
            raise HH001CommitmentError("The contrast must name two different arms")

    @property
    def below_confirmatory_replicates(self) -> bool:
        return self.replicates < CONFIRMATORY_MIN_REPLICATES

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["arms"] = list(self.arms)
        payload["contrast"] = list(self.contrast)
        payload["schema"] = "hh001-commitments-v1"
        payload["below_confirmatory_replicates"] = self.below_confirmatory_replicates
        return payload

    def canonical_bytes(self) -> bytes:
        return (
            json.dumps(self.as_dict(), ensure_ascii=True, indent=1, sort_keys=True) + "\n"
        ).encode("utf-8")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def write(self, path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.canonical_bytes())
        return self.digest

    @classmethod
    def load(cls, path: Path) -> "Commitments":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            arms=tuple(payload["arms"]),
            primary_endpoint=payload["primary_endpoint"],
            cross_check_endpoint=payload["cross_check_endpoint"],
            budget_chars=int(payload["budget_chars"]),
            subsample_size=int(payload["subsample_size"]),
            replicates=int(payload["replicates"]),
            contrast=(payload["contrast"][0], payload["contrast"][1]),
            seed=str(payload["seed"]),
            population=str(payload["population"]),
            plan_sha256=str(payload.get("plan_sha256", "")),
            template_manifest=dict(payload.get("template_manifest", {})),
        )


def default_commitments(
    *, subsample_size: int, replicates: int, plan_sha256: str = "",
    template_manifest: dict[str, str] | None = None,
) -> Commitments:
    """The plan's §6 list, with the two pilot-set values supplied by the caller.

    ``subsample_size`` and ``replicates`` come from the timing pilot and are
    written down before any outcome is seen. Everything else is fixed by the
    plan and is not a runtime choice.
    """
    return Commitments(
        arms=(
            "A0_NO_MEMORY",
            "A1_FULL_CONTEXT",
            "A2_CDW_PAIR",
            "A3_MEM0",
            "A4_RAG_FIXED",
        ),
        primary_endpoint="judged",
        cross_check_endpoint="contained",
        budget_chars=16_000,
        subsample_size=subsample_size,
        replicates=replicates,
        contrast=("A2_CDW_PAIR", "A3_MEM0"),
        plan_sha256=plan_sha256,
        template_manifest=dict(template_manifest or {}),
    )


def verify_run(
    commitments: Commitments,
    *,
    arms_run: tuple[str, ...],
    budget_chars: int,
    items_scored: int,
    replicates: int,
    template_manifest: dict[str, str] | None = None,
) -> None:
    """Refuse a result that does not match what was committed.

    Every mismatch is a stop, not a warning. A run that quietly dropped an arm
    or shortened the sample and then reported a contrast would be exactly the
    thing the commitments exist to prevent.
    """
    missing = set(commitments.arms) - set(arms_run)
    if missing:
        raise HH001CommitmentError(
            f"Committed arms did not run: {sorted(missing)}. "
            "Dropping an arm requires amending the commitments before the run."
        )
    extra = set(arms_run) - set(commitments.arms)
    if extra:
        raise HH001CommitmentError(f"Uncommitted arms ran: {sorted(extra)}")
    if budget_chars != commitments.budget_chars:
        raise HH001CommitmentError(
            f"Budget {budget_chars} differs from the committed "
            f"{commitments.budget_chars}"
        )
    if items_scored != commitments.subsample_size:
        raise HH001CommitmentError(
            f"Scored {items_scored} items against a committed "
            f"{commitments.subsample_size}"
        )
    if replicates != commitments.replicates:
        raise HH001CommitmentError(
            f"Ran {replicates} replicates against a committed "
            f"{commitments.replicates}"
        )
    if template_manifest is not None and commitments.template_manifest:
        if template_manifest != commitments.template_manifest:
            raise HH001CommitmentError(
                "Prompt templates changed after the commitments were written; "
                "one template, byte-identical across arms, is the whole point"
            )


def plan_digest(repo_root: Path) -> str:
    """LF-normalized digest of the plan this run is executing."""
    path = repo_root / PLAN
    if not path.is_file():
        raise HH001CommitmentError(f"Development plan not found at {path}")
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


__all__ = [
    "CONFIRMATORY_MIN_REPLICATES",
    "Commitments",
    "HH001CommitmentError",
    "PLAN",
    "default_commitments",
    "plan_digest",
    "verify_run",
]
