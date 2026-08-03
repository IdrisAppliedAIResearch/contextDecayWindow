"""Register EC-001's Tier 2 subset before any Tier 1 result exists."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    EXPECTED_STRATA,
    EC001Error,
    assert_repository_ready,
    build_subset_manifest,
    load_adaptation_record,
    load_longmemeval,
    validate_subset_manifest,
)


def parse_quota(values: list[str]) -> dict[str, int]:
    quotas: dict[str, int] = {}
    for value in values:
        name, separator, count = value.partition("=")
        if not separator:
            raise EC001Error(f"Quota must have STRATUM=COUNT form: {value!r}")
        if name in quotas:
            raise EC001Error(f"Duplicate quota: {name}")
        try:
            quotas[name] = int(count)
        except ValueError as error:
            raise EC001Error(f"Invalid quota count: {value!r}") from error
    return quotas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--quota",
        action="append",
        default=[],
        metavar="STRATUM=COUNT",
        help=(
            "Required once for every stratum: "
            + ", ".join(EXPECTED_STRATA)
        ),
    )
    args = parser.parse_args()

    assert_repository_ready(require_clean=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite subset: {args.output}")
    record = load_adaptation_record()
    benchmark = record["benchmark"]
    if args.data.stat().st_size != int(benchmark["dataset_bytes"]):
        raise EC001Error("Dataset byte size does not match the adaptation pin")
    dataset = load_longmemeval(
        args.data,
        expected_sha256=str(benchmark["dataset_sha256"]),
    )
    manifest = build_subset_manifest(
        dataset,
        parse_quota(args.quota),
        seed=args.seed,
    )
    validate_subset_manifest(manifest, dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Registered {manifest['size']} Tier 2 questions at {args.output}. "
        "Commit this file before running Tier 1."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
