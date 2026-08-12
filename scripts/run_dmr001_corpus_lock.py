"""Freeze the DMR-001 episode corpus and write its content-addressed manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import (  # noqa: E402
    corpus_manifest,
    select_sessions,
    write_json,
)

DEFAULT_OUTPUT = (
    ROOT
    / "experiments"
    / "components"
    / "biological_memory"
    / "dmr_001"
    / "artifacts"
    / "dmr001_corpus"
    / "corpus_lock.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    sessions = select_sessions(ROOT)
    manifest = corpus_manifest(sessions)
    digest = write_json(
        arguments.output, manifest, allow_overwrite=arguments.allow_overwrite
    )

    counts = manifest["counts"]
    print("DMR-001 corpus lock")
    print(f"  sessions            : {counts['sessions']}")
    print(f"  episodes            : {counts['episodes']}")
    print(
        f"  development         : {counts['development_sessions']} sessions, "
        f"{counts['development_episodes']} episodes, "
        f"{counts['development_annotated_boundaries']} annotated boundaries"
    )
    print(
        f"  holdout             : {counts['holdout_sessions']} sessions, "
        f"{counts['holdout_episodes']} episodes, "
        f"{counts['holdout_annotated_boundaries']} annotated boundaries"
    )
    print(f"  corpus digest       : {manifest['corpus_digest']}")
    print(f"  artifact sha256     : {digest}")
    print(f"  artifact            : {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
