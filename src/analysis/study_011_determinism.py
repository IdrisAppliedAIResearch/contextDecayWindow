"""Study 011 section 5: the determinism spot-check.

The standing rule asks for a byte-identical seeded prefix rerun. This
compares a rerun against the committed run turn by turn on three things,
in the order they can fail:

1. the constructed prompt, which is what the mechanism produced;
2. the retrieval payload digest, which is what the packer produced;
3. the assistant response, which is what the model produced.

Separating them matters. A mechanism that is deterministic under a model
that is not still gives an identical prompt and a different answer, and
that is a materially different finding from a mechanism that drifts. The
check reports the first turn at which each diverges rather than a single
pass or fail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"


class DeterminismError(RuntimeError):
    """Raised when the comparison cannot be made."""


def _repo_relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _read_jsonl(path: Path) -> dict[int, dict]:
    if not path.is_file():
        raise DeterminismError(f"missing log: {path}")
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[int(row["turn_number"])] = row
    return rows


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare(original: Path, rerun: Path) -> dict:
    left_turns = _read_jsonl(original / "logs" / "turns.jsonl")
    right_turns = _read_jsonl(rerun / "logs" / "turns.jsonl")
    left_ctx = _read_jsonl(original / "logs" / "context_match.jsonl")
    right_ctx = _read_jsonl(rerun / "logs" / "context_match.jsonl")

    shared = sorted(set(left_turns) & set(right_turns))
    if not shared:
        raise DeterminismError("the two runs share no turns")

    rows = []
    first_divergence = {"prompt": None, "payload": None, "response": None}
    for turn in shared:
        left_prompt = (original / "constructed_prompts" / f"turn_{turn:03d}.txt")
        right_prompt = (rerun / "constructed_prompts" / f"turn_{turn:03d}.txt")
        prompt_same = (
            left_prompt.is_file()
            and right_prompt.is_file()
            and left_prompt.read_bytes() == right_prompt.read_bytes()
        )
        payload_same = (
            left_ctx[turn]["retrieval_payload_sha256"]
            == right_ctx[turn]["retrieval_payload_sha256"]
        )
        response_same = _digest(
            str(left_turns[turn].get("assistant_message") or "")
        ) == _digest(str(right_turns[turn].get("assistant_message") or ""))

        for name, same in (
            ("prompt", prompt_same),
            ("payload", payload_same),
            ("response", response_same),
        ):
            if not same and first_divergence[name] is None:
                first_divergence[name] = turn

        rows.append(
            {
                "turn": turn,
                "prompt_identical": prompt_same,
                "payload_digest_identical": payload_same,
                "response_identical": response_same,
            }
        )

    identical = {
        name: sum(1 for row in rows if row[f"{key}_identical"])
        for name, key in (
            ("prompt", "prompt"),
            ("payload_digest", "payload_digest"),
            ("response", "response"),
        )
    }
    mechanism_deterministic = first_divergence["prompt"] is None and (
        first_divergence["payload"] is None
    )
    return {
        "study": "011",
        "check": "determinism spot-check (section 5)",
        "original": _repo_relative(original),
        "rerun": _repo_relative(rerun),
        "turns_compared": len(shared),
        "identical_counts": identical,
        "first_divergence_turn": first_divergence,
        "mechanism_deterministic": mechanism_deterministic,
        "response_deterministic": first_divergence["response"] is None,
        "status": "PASS" if mechanism_deterministic else "FAIL",
        "what_this_certifies": (
            "The mechanism -- prompt construction and packing -- is what this "
            "gate binds. A model that is not bit-reproducible under a fixed "
            "seed produces an identical prompt and a different answer; that "
            "is reported separately and does not fail the mechanism check."
        ),
        "per_turn": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--rerun", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=STUDY_ROOT / "runtime" / "determinism.json",
    )
    args = parser.parse_args(argv)

    try:
        result = compare(args.original, args.rerun)
    except DeterminismError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    counts = result["identical_counts"]
    total = result["turns_compared"]
    print(f"turns compared: {total}")
    print(f"  prompts identical:        {counts['prompt']}/{total}")
    print(f"  payload digests identical:{counts['payload_digest']}/{total}")
    print(f"  responses identical:      {counts['response']}/{total}")
    print(f"mechanism: {result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
