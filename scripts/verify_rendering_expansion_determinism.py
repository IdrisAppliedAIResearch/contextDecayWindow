from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare two DR-001 artifact directories byte-for-byte."
    )
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--repeat", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    primary = _hash_directory(args.primary)
    repeat = _hash_directory(args.repeat)
    names_match = set(primary) == set(repeat)
    files = [
        {
            "name": name,
            "primary_sha256": primary.get(name),
            "repeat_sha256": repeat.get(name),
            "match": primary.get(name) == repeat.get(name),
        }
        for name in sorted(set(primary) | set(repeat))
    ]
    status = (
        "PASS"
        if names_match and all(item["match"] for item in files)
        else "FAIL"
    )
    payload = {
        "check": "DR-001 offline replay determinism",
        "status": status,
        "separate_processes": True,
        "file_sets_match": names_match,
        "files": files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Determinism {status}")
    if status != "PASS":
        raise SystemExit(1)


def _hash_directory(path: Path) -> dict[str, str]:
    return {
        file.relative_to(path).as_posix(): _sha256(file)
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()

