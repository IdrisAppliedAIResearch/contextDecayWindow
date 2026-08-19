"""Gate PAPER-002 against the evidence spine and the withdrawn-claim list.

Two checks the academic-research-skills integrity stage cannot do, because its
citation gate verifies *external* references against Semantic Scholar, OpenAlex,
Crossref and arXiv, and every headline number in this paper is internal.

  1. NUMBER TRACE. Every distinct numeric literal in `paper/PAPER_002.md` must
     also appear in `paper/notes/EVIDENCE_SPINE.md`. A number that appears in the
     paper and nowhere in the spine is either untraced or newly invented, and both
     are defects under AGENTS.md section 8.

  2. WITHDRAWN VALUES. Every superseded value listed in
     `paper/notes/DO_NOT_WRITE.md` section 6 must be absent from the paper. This is
     run as a grep for the superseded *value*, not the superseded sentence, which
     the PASS_6 slop audit records as the only method that works.

Neither check can prove a claim is right. They catch the two failure modes this
repository has actually committed: a number that drifted from its artifact, and a
withdrawn claim that came back during a rewrite because it was the cleaner sentence.

COVERAGE BOUNDARY, stated because a gate whose limits are unstated invites the
reading that it checked everything. Bare integers of `PROSE_CEILING` or less are
exempt, since at that size a numeral is usually prose rather than measurement. That
exempts real claims: "5 of 17 across 2 domains", "12 domains to 2", "10 of 10 facts
used". Those are traced by hand in EVIDENCE_SPINE.md section 7.13 and rest on review,
not on this script. Lowering the ceiling does not fix it -- it drowns the signal --
so the boundary is documented instead of closed.

Exit code 0 if both checks pass, 1 otherwise.

Usage, from the repository root:

    python scripts/check_paper_002_claims.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAPER = REPO / "paper/PAPER_002.md"
SPINE = REPO / "paper/notes/EVIDENCE_SPINE.md"
FORBIDDEN = REPO / "paper/notes/DO_NOT_WRITE.md"

# Numbers small enough to be prose rather than measurement ("three constraints",
# "the first two"). Section numbers and years are handled separately.
PROSE_CEILING = 20

# Bare section/figure references and dates are structural, not claims.
_STRIP = [
    re.compile(r"^#{1,6}\s+\d+(?:\.\d+)*", re.M),  # section heading numbers
    re.compile(r"§\s*\d+(?:\.\d+)*"),           # section cross-references
    re.compile(r"[Ff]igure\s+\d+"),             # figure references
    re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),     # ISO dates
    re.compile(r"`[^`]*`"),                     # inline code: paths, SHAs, symbols
    re.compile(r"^\s*\|?\s*-{2,}.*$", re.M),    # table rules
    re.compile(r"^\s{0,3}\d+\.\s", re.M),       # ordered-list markers
]

_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?(?:e[+-]?\d+)?", re.I)


def normalize(token: str) -> str:
    """Canonical form for comparison: drop thousands separators, keep scale."""
    return token.replace(",", "").rstrip(".").lower()


def harvest(text: str) -> set[str]:
    """Every numeric literal in `text`, normalized, after stripping structure."""
    for pattern in _STRIP:
        text = pattern.sub(" ", text)
    return {normalize(m.group()) for m in _NUMBER.finditer(text)}


def is_prose_number(token: str) -> bool:
    """True for small bare integers that read as words rather than measurements."""
    try:
        value = float(token)
    except ValueError:
        return False
    return value.is_integer() and 0 <= value <= PROSE_CEILING


def check_number_trace() -> list[str]:
    """Numbers present in the paper and absent from the spine."""
    paper_numbers = harvest(PAPER.read_text(encoding="utf-8"))
    spine_numbers = harvest(SPINE.read_text(encoding="utf-8"))

    untraced = {
        token
        for token in paper_numbers - spine_numbers
        if not is_prose_number(token)
    }
    return sorted(untraced, key=lambda t: (-len(t), t))


def forbidden_values() -> list[tuple[str, str]]:
    """(value, why) pairs from the ```superseded fence in DO_NOT_WRITE.md.

    Only values with no legitimate corrective use belong there. A value the paper
    names *while correcting it* is recorded in EVIDENCE_SPINE.md section 7.11
    instead, because naming a superseded figure in order to give the corrected one
    is how ERRATA.md records a correction — the opposite of restating the claim.
    """
    rows: list[tuple[str, str]] = []
    inside = False
    for line in FORBIDDEN.read_text(encoding="utf-8").splitlines():
        if line.startswith("```superseded"):
            inside = True
            continue
        if inside and line.startswith("```"):
            break
        if not inside or "|" not in line:
            continue
        value, _, why = line.partition("|")
        value = value.strip()
        if _NUMBER.fullmatch(value):
            rows.append((normalize(value), why.strip()))
    return rows


def check_forbidden() -> list[str]:
    """Superseded values that reappear in the paper."""
    paper_numbers = harvest(PAPER.read_text(encoding="utf-8"))
    return [
        f"{value} — superseded by: {why}"
        for value, why in forbidden_values()
        if value in paper_numbers
    ]


def main() -> int:
    for path in (PAPER, SPINE, FORBIDDEN):
        if not path.exists():
            print(f"MISSING: {path.relative_to(REPO).as_posix()}")
            return 1

    untraced = check_number_trace()
    revived = check_forbidden()

    print("PAPER-002 claim gates")
    print("=" * 60)

    if untraced:
        print(f"\nNUMBER TRACE: FAIL — {len(untraced)} untraced")
        print("Each appears in the paper and nowhere in EVIDENCE_SPINE.md.")
        print("Trace it to a committed artifact, add it to the spine, or cut it.\n")
        for token in untraced:
            print(f"  {token}")
    else:
        print("\nNUMBER TRACE: PASS — every measurement traces to the spine")

    if revived:
        print(f"\nWITHDRAWN VALUES: FAIL — {len(revived)} revived\n")
        for item in revived:
            print(f"  {item}")
    else:
        print("WITHDRAWN VALUES: PASS — no superseded value reappears")

    print()
    return 1 if (untraced or revived) else 0


if __name__ == "__main__":
    sys.exit(main())
