"""Freeze the DMR-001C LongMemEval stream corpus and write its manifest."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis.dmr001_corpus import write_json  # noqa: E402
from src.analysis.dmr001c_corpus import load_corpus  # noqa: E402

DEFAULT_DATA = Path(r"C:\Users\muzaf\datasets\longmemeval\longmemeval_s_cleaned.json")
DEFAULT_CACHE = (
    ROOT / "experiments/external/longmemeval/runs/ec002_k_first/ec002_exact_solo_embeddings.db"
)
DEFAULT_OUTPUT = (
    ROOT
    / "experiments/components/biological_memory/dmr_001c/artifacts/dmr001c_corpus/corpus_lock.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allow-overwrite", action="store_true")
    arguments = parser.parse_args()

    streams, manifest = load_corpus(arguments.data, arguments.cache)
    digest = write_json(arguments.output, manifest, allow_overwrite=arguments.allow_overwrite)

    counts = manifest["counts"]
    print("DMR-001C corpus lock")
    print(f"  streams              : {counts['streams']}")
    print(f"  episodes             : {counts['episodes']}")
    print(f"  source sessions      : {counts['source_sessions']}")
    print(f"  seams (annotations)  : {counts['seams']}")
    print(f"  excluded             : {manifest['excluded']['irregular_sessions']} irregular sessions, "
          f"{len(manifest['excluded']['streams_below_minimum'])} streams")
    lengths = sorted(row["episode_count"] for row in manifest["streams"])
    if lengths:
        print(f"  episodes per stream  : min {lengths[0]} med {lengths[len(lengths)//2]} max {lengths[-1]}")
    print(f"  corpus digest        : {manifest['corpus_digest']}")
    print(f"  artifact sha256      : {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
