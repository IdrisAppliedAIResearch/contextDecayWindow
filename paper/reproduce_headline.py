"""Reproduce one of PAPER-001's headline numbers from committed data.

The claim under test, from §5.1:

    The exact minimum for 14 of 17 breadth items is 5,058 characters across
    five episodes, against a 32,000-character budget.

This script rebuilds that payload from the committed turn log using the
installed `episodic` package's serialization contract, and checks both its
length and its SHA-256 against the values AR-001 committed.

It needs no model, no embedder, no network, and no database. The renderer is a
pure function of episode text, which is why this check is possible at all.

Usage, from the repository root, with `episodic` installed:

    python paper/reproduce_headline.py

Exit code 0 means reproduced.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# The serialization contract. `_render` is private to the package because
# callers are meant to go through EpisodeStore.context(); it is used directly
# here because reproducing a committed payload means rendering a specific set of
# episodes, not running retrieval over a store.
from episodic._render import render_stm_payload

REPO = Path(__file__).resolve().parent.parent

ACHIEVABILITY = (
    REPO
    / "experiments/components/retrieval_mechanism_ledger"
    / "artifacts/ar_001/achievability.json"
)
TURN_LOG = (
    REPO
    / "experiments/surveys/retrieval_bakeoff/tier6/runs"
    / "tier6_live_121_corrected_001/context_matched_stm/logs/turns.jsonl"
)


def main() -> int:
    for path in (ACHIEVABILITY, TURN_LOG):
        if not path.exists():
            print(f"FAIL  missing committed input: {path}")
            return 1

    expected = json.loads(ACHIEVABILITY.read_text(encoding="utf-8"))["exact_optimum"]
    wanted_turns = expected["selected_source_turns"]

    turns = {}
    for line in TURN_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            turns[row["turn_number"]] = row

    missing = [t for t in wanted_turns if t not in turns]
    if missing:
        print(f"FAIL  turn log is missing turns {missing}")
        return 1

    episodes = [
        {
            "turn_number": turn,
            "user_message": turns[turn]["user_message"],
            "assistant_message": turns[turn]["assistant_message"],
        }
        for turn in wanted_turns
    ]

    payload = render_stm_payload([], episodes)
    chars = len(payload)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    checks = [
        ("episode count", len(episodes), expected["episode_count"]),
        ("serialized characters", chars, expected["serialized_chars"]),
        ("payload SHA-256", digest, expected["payload_sha256"]),
    ]

    print(f"turns rebuilt from the committed log: {wanted_turns}")
    ok = True
    for name, got, want in checks:
        matched = got == want
        ok = ok and matched
        print(f"  [{'OK ' if matched else 'BAD'}] {name}: {got}"
              + ("" if matched else f"  (committed: {want})"))

    print()
    if ok:
        print(
            f"REPRODUCED  14 of 17 breadth items are available in "
            f"{chars:,} characters of a 32,000-character budget "
            f"({chars / 32000:.1%} of it), across "
            f"{len(episodes)} episodes."
        )
        return 0

    print("NOT REPRODUCED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
