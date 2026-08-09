"""Build blind packets and the sealed mapping for the five replicates.

Item construction is Study 011's, imported rather than reimplemented:
same question-to-turn map, same reasoning-block stripping, same
`NO_ANSWER` rule, same spanning treatment for Q13. A Phase 2 packet that
differed from a Study 011 packet in any of those would make the band a
measurement of two rubrics rather than one instrument.

Only the sealing is new, because there are five labels rather than four
and because run order is the one thing a rater could anchor on when every
replicate is the same configuration. Labels come from response digests.

Run this before any rater sees anything, and commit its output before the
first pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.amendment_001_noise_band import (  # noqa: E402
    NOISE_BAND_ROOT,
    NoiseBandError,
    REPLICATES,
    assert_decision_rule,
    seal_replicates,
)
from src.analysis.study_011_scoring import build_packets  # noqa: E402

RUNS_ROOT = NOISE_BAND_ROOT / "runs"
EVALUATION = NOISE_BAND_ROOT / "evaluation"
RUN_MANIFEST = NOISE_BAND_ROOT / "run_manifest.json"


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def discover_runs(manifest_path: Path) -> dict[str, Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    runs = {
        row["run_id"]: Path(row["output_dir"])
        for row in manifest["replicates"]
    }
    if len(runs) != REPLICATES:
        raise NoiseBandError(
            f"the run manifest lists {len(runs)} replicates, not {REPLICATES}"
        )
    missing = [name for name, path in runs.items() if not path.is_dir()]
    if missing:
        raise NoiseBandError(f"missing replicate directories: {missing}")
    return runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=RUN_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=EVALUATION)
    args = parser.parse_args(argv)

    try:
        # The decision rule must already be committed and unchanged. A
        # packet built after a quietly edited rule is worthless.
        rule_digest = assert_decision_rule()
        runs = discover_runs(args.manifest)
        mapping = seal_replicates(runs)
        packets = build_packets(runs, mapping)
    except NoiseBandError as error:
        print(f"STOP: {error}", file=sys.stderr)
        return 1

    # The rater instructions are Study 011's file, referenced rather than
    # copied. Two copies of a rubric are two rubrics waiting to drift, and
    # the standing rule is that rubrics stay byte-identical.
    packets["rater_instructions"] = (
        "experiments/study_011/evaluation/RATER_INSTRUCTIONS.md"
    )
    packets["rater_instructions_sha256_lf"] = _sha256_lf(
        REPO_ROOT / "experiments" / "study_011" / "evaluation"
        / "RATER_INSTRUCTIONS.md"
    )
    packets["phase"] = "2"
    packets["design"] = (
        f"Arm D, the deployed configuration, repeated N = {REPLICATES}. "
        "Every packet is one replicate's answer to one rubric question."
    )
    packets["decision_rule_sha256_lf"] = rule_digest
    packets["blinding_note"] = (
        "The replicates are the same configuration, so run order is the only "
        "thing a rater could anchor on. Labels are assigned by response "
        "digest and carry no ordering information."
    )

    args.output_root.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("sealed_mapping.json", mapping),
        ("blind_packets.json", packets),
    ):
        (args.output_root / name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    no_answer = [row["item_id"] for row in packets["items"] if row["no_answer"]]
    print(f"items: {packets['item_count']} across {len(runs)} blind labels")
    print(f"NO_ANSWER items (score 0 by protocol): {len(no_answer)}")
    print("sealed mapping written; do not open until blind scores are committed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
