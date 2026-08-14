"""Capture vectors or analyse the locked LoCoMo development split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "episodic" / "src"))

from analysis.locomo_nf_development import (  # noqa: E402
    adapt_development,
    analyse,
    capture_vectors,
    inventory,
)


def write_json(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("inventory", "capture", "analyse"))
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path)
    parser.add_argument("--embedding-cache", type=Path)
    parser.add_argument("--vector-manifest", type=Path)
    args = parser.parse_args()

    conversations = adapt_development(args.data)
    if args.mode == "inventory":
        payload = inventory(conversations)
    elif args.mode == "capture":
        if args.embedding_model is None or args.embedding_cache is None:
            parser.error("capture requires --embedding-model and --embedding-cache")
        payload = capture_vectors(
            conversations, args.embedding_model, args.embedding_cache
        )
    else:
        if args.embedding_cache is None or args.vector_manifest is None:
            parser.error("analyse requires --embedding-cache and --vector-manifest")
        manifest = json.loads(args.vector_manifest.read_text(encoding="utf-8"))
        payload = analyse(conversations, args.embedding_cache, manifest)
    write_json(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
