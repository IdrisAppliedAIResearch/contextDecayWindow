"""Prepare deterministic anonymous Study 010 scoring inputs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "experiments/study_010/runs/study_010_full_001"
OUT = ROOT / "experiments/study_010/evaluation"
PROBE_TURNS = (250, 251, 252, 500, 501, 502, 750, 751, 752, *range(987, 1001))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_probes(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    sections = {
        int(match.group(1)): match.group(0).rstrip()
        for match in re.finditer(
            r"(?ms)^## Turn (\d+)\s*$.*?(?=^## Turn \d+\s*$|\Z)", text
        )
    }
    missing = [turn for turn in PROBE_TURNS if turn not in sections]
    if missing:
        raise RuntimeError(f"{path} is missing probe turns: {missing}")
    return "# Anonymous Study 010 Probe Responses\n\n" + "\n\n".join(
        sections[turn] for turn in PROBE_TURNS
    ) + "\n"


def main() -> None:
    sources = {
        "arm_l": RUN / "arm_l/rubric/responses.md",
        "arm_s": RUN / "arm_s/rubric/responses.md",
    }
    hashes = {name: sha256(path) for name, path in sources.items()}
    combined = hashlib.sha256(
        f"{hashes['arm_l']}:{hashes['arm_s']}".encode("ascii")
    ).hexdigest()
    ordered = ("arm_l", "arm_s") if int(combined[0], 16) % 2 == 0 else ("arm_s", "arm_l")
    mapping = {"arm_A": ordered[0], "arm_B": ordered[1]}

    OUT.mkdir(parents=True, exist_ok=True)
    for anonymous, source_name in mapping.items():
        destination = OUT / anonymous / "responses.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(extract_probes(sources[source_name]), encoding="utf-8")

    sealed = {
        "sealed": True,
        "do_not_open": (
            "Open only after evaluation/rubric_scores.json is committed. "
            "Git history is the audit trail."
        ),
        "mapping": mapping,
        "assignment_source": (
            "Parity of the first hexadecimal digit of SHA-256 over the ordered "
            "Arm L and Arm S rubric-response hashes."
        ),
        "response_sha256": hashes,
        "combined_sha256": combined,
        "anonymous_response_sha256": {
            anonymous: sha256(OUT / anonymous / "responses.md")
            for anonymous in mapping
        },
    }
    (OUT / "sealed_mapping.json").write_text(
        json.dumps(sealed, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "scoring_protocol.md").write_text(
        """# Study 010 Blinded Scoring Protocol

The two files under `arm_A/` and `arm_B/` contain only the 23 registered
probe exchanges. Anonymous assignment is hash-derived and recorded in
`sealed_mapping.json`.

The rater receives only these anonymous files, the locked rubric, and the
scoring-integrity protocol. It must produce primary and strict scores plus a
rationale for every arm-question pair. The sealed mapping and full-run
mechanism logs remain unopened until the score artifact is committed.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
