"""Adopt and validate EC-002's retained pre-contract vector cache read-only."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "episodic" / "src"))

from episodic import EmbeddingCache  # noqa: E402
from episodic._embedding import SENTINEL_TEXT  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--file-sha256", required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite output: {args.output}")

    adoption = EmbeddingCache.inspect_legacy_v0(
        args.cache,
        expected_file_sha256=args.file_sha256,
        expected_model_sha256=args.model_sha256,
    )
    with EmbeddingCache(
        args.cache,
        mode="reuse",
        expected_file_sha256=adoption["file_sha256"],
        expected_content_sha256=adoption["content_sha256"],
        expected_model_sha256=args.model_sha256,
        legacy_v0=True,
    ) as cache:
        cache(SENTINEL_TEXT)
        reuse = cache.record()

    after = EmbeddingCache.inspect_legacy_v0(
        args.cache,
        expected_file_sha256=adoption["file_sha256"],
        expected_model_sha256=args.model_sha256,
    )
    passed = (
        adoption["entries"] == 96_585
        and reuse["hits"] == 1
        and reuse["misses"] == 0
        and after["file_sha256"] == adoption["file_sha256"]
        and after["content_sha256"] == adoption["content_sha256"]
    )
    result = {
        "record": "CC-006 C9 EC-002 legacy-cache adoption",
        "status": "PASS" if passed else "FAIL",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "expected_entries": 96_585,
        "adoption": adoption,
        "reuse": reuse,
        "after": after,
        "zero_model_calls_by_construction": True,
        "note": (
            "No delegate was supplied in reuse mode; a miss would raise "
            "before any model call."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"CC-006 C9: {result['status']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
