"""Generate the post-run EC-001 retrieval-path diagnostic."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import load_longmemeval, sha256_file  # noqa: E402
from src.analysis.ec001_retrieval_path import (  # noqa: E402
    build_retrieval_path_diagnostic,
)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def read_mechanism_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            row.pop("block", None)
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--mechanism", type=Path, required=True)
    parser.add_argument("--run-header", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite diagnostic: {args.output}")
    header = json.loads(args.run_header.read_text(encoding="utf-8"))
    dataset = load_longmemeval(
        args.data,
        expected_sha256=str(header["dataset_sha256"]),
    )
    config = header["episodic_config"]
    result = build_retrieval_path_diagnostic(
        dataset=dataset,
        score_rows=read_jsonl(args.scores),
        mechanism_rows=read_mechanism_jsonl(args.mechanism),
        k_threshold=float(config["k_threshold"]),
        recency_window_n=int(config["recency_window_n"]),
    )
    result["inputs"] = {
        "dataset_sha256": sha256_file(args.data),
        "tier1_scores_sha256": sha256_file(args.scores),
        "sealed_mechanism_sha256": sha256_file(args.mechanism),
        "run_header_sha256": sha256_file(args.run_header),
        "analysis_script_sha256": sha256_file(Path(__file__)),
    }
    args.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
