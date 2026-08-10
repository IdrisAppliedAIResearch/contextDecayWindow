"""Replay the exact prompt whose divergence Study 011 recorded.

Phase 1's registered prompt set is drawn from Arm D's committed windows
and reproduced on all 800 generations. That leaves an obvious gap: the
divergence the amendment is built on was observed on a *different*
prompt — Arm A's ablation turn 1, 757 bytes — and a probe that never
issues that prompt cannot say anything about it.

This replays it. Same provider, same call shape, same server settings,
one process, N generations. The two committed responses are 343 and 80
characters, so the question is whether either recurs, whether both do,
and whether anything else appears.

Beyond §3.2, disclosed as an addition, and able only to find more
divergence than the registered conditions found.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_amendment_001_phase_1 import (  # noqa: E402
    MODEL_PATH,
    SEED,
    Server,
    _completion,
)
from src.analysis.study_011_sampling_determinism import first_divergence  # noqa: E402

STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
ABLATION_RUNS = STUDY_ROOT / "ablation_runs"
RECORDED_PROMPT = (
    ABLATION_RUNS / "study_011_ablation_a" / "arm_a" / "constructed_prompts" / "turn_001.txt"
)
COMMITTED_RUNS = {
    "ablation": ABLATION_RUNS / "study_011_ablation_a" / "arm_a",
    "determinism_rerun": ABLATION_RUNS / "study_011_determinism_a" / "arm_a",
}
DEFAULT_OUTPUT = STUDY_ROOT / "runtime" / "phase_1_recorded_prompt_replay.json"
GENERATIONS = 20


def committed_response(directory: Path, turn: int = 1) -> str:
    rows = [
        json.loads(line)
        for line in (directory / "logs" / "turns.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    for row in rows:
        if int(row["turn_number"]) == turn:
            return str(row.get("assistant_message") or "")
    raise RuntimeError(f"no turn {turn} in {directory}")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generations", type=int, default=GENERATIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    prompt = RECORDED_PROMPT.read_text(encoding="utf-8")
    committed = {
        name: committed_response(path) for name, path in COMMITTED_RUNS.items()
    }
    if committed["ablation"] == committed["determinism_rerun"]:
        raise SystemExit(
            "the two committed responses are identical; there is no recorded "
            "divergence to replay"
        )

    outputs: list[str] = []
    log_dir = STUDY_ROOT / "runtime" / "phase_1_logs"
    with Server("1", log_dir, "recorded_prompt_replay") as server:
        server_record = {
            "server_pid": server.process.pid,
            "server_build_hash": server.props["build_info"],
            "server_command": " ".join(server.command),
        }
        for index in range(args.generations):
            output = _completion(prompt)
            outputs.append(output)
            print(f"  generation {index + 1}/{args.generations}: {len(output)} chars", flush=True)

    digests = [_digest(text) for text in outputs]
    counts = Counter(digests)
    matches = {
        name: sum(1 for text in outputs if text == body)
        for name, body in committed.items()
    }
    report = {
        "study": "011",
        "amendment": (
            "experiments/study_011/amendments/"
            "AMENDMENT_001_determinism_and_noise_band.md"
        ),
        "phase": "1",
        "title": "replay of the exact prompt whose divergence is recorded",
        "scope": (
            "Beyond §3.2. Phase 1's registered prompt set is drawn from Arm D "
            "windows and reproduced on all 800 generations; the recorded "
            "divergence was observed on Arm A's ablation turn 1, which that "
            "set never issues. Disclosed as an addition; it can only find "
            "more divergence than the registered conditions found."
        ),
        "prompt": {
            "path": RECORDED_PROMPT.relative_to(REPO_ROOT).as_posix(),
            "bytes": len(prompt.encode("utf-8")),
            "sha256": _digest(prompt),
        },
        "committed_responses": {
            name: {
                "characters": len(body),
                "sha256": _digest(body),
                "path": (
                    COMMITTED_RUNS[name].relative_to(REPO_ROOT).as_posix()
                    + "/logs/turns.jsonl"
                ),
            }
            for name, body in committed.items()
        },
        "committed_divergence_char": first_divergence(
            committed["ablation"], committed["determinism_rerun"]
        ),
        "replay": {
            "generations": args.generations,
            "distinct_outputs": len(counts),
            "identical_across_all_generations": len(counts) == 1,
            "output_lengths": [len(text) for text in outputs],
            "output_sha256": digests,
            "most_common_count": counts.most_common(1)[0][1],
        },
        "matches_committed": matches,
        "runtime": {
            "model": str(MODEL_PATH),
            "seed": SEED,
            "temperature": 1.0,
            "parallel_slots": 1,
            "speculative_decoding": "none",
            **server_record,
            "measured_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    reproduced_either = sum(matches.values())
    if len(counts) > 1:
        report["finding"] = (
            "The recorded divergence reproduces on this prompt: the same "
            "bytes produced more than one response within a single process."
        )
    elif reproduced_either:
        report["finding"] = (
            "The prompt reproduced a single response across every generation, "
            "and that response is one of the two committed ones. The runtime "
            "is stable here; whatever produced the other committed response "
            "is not present in this process."
        )
    else:
        report["finding"] = (
            "The prompt reproduced a single response across every generation, "
            "and it matches neither committed response. The runtime is stable "
            "within this process but does not reproduce either recorded run, "
            "which points at process-level state rather than at sampling."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"\nwrote {args.output}")
    print(f"  distinct outputs: {len(counts)} across {args.generations} generations")
    print(f"  matches committed: {matches}")
    print(f"  {report['finding']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
