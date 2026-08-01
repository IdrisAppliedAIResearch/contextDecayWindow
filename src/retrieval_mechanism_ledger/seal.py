from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def verify_mixed_source_seal(repo_root: Path, run_root: Path) -> dict:
    seal = json.loads(
        (run_root / "mechanism_seal.json").read_text(encoding="utf-8")
    )
    expected_files = dict(seal["mechanism_files"])
    run_relative = run_root.relative_to(repo_root).as_posix()
    verified: dict[str, str] = {}
    mismatches = []
    representations = {
        "sealed_canonical_lf": 0,
        "sealed_materialized_crlf": 0,
        "exact_untracked_binary": 0,
    }

    for relative, expected in sorted(expected_files.items()):
        path = run_root / relative
        if not path.is_file():
            mismatches.append(
                {
                    "path": relative,
                    "status": "MISSING",
                    "expected": expected,
                    "actual": None,
                }
            )
            continue
        repository_path = f"{run_relative}/{relative}"
        tracked = (
            subprocess.run(
                ["git", "cat-file", "-e", f"HEAD:{repository_path}"],
                cwd=repo_root,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        checkout = path.read_bytes()
        checkout_digest = hashlib.sha256(checkout).hexdigest()
        if not tracked:
            if checkout_digest != expected:
                mismatches.append(
                    {
                        "path": relative,
                        "status": "UNTRACKED_HASH_MISMATCH",
                        "expected": expected,
                        "actual": checkout_digest,
                    }
                )
                continue
            verified[relative] = expected
            representations["exact_untracked_binary"] += 1
            continue

        blob = subprocess.check_output(
            ["git", "show", f"HEAD:{repository_path}"],
            cwd=repo_root,
        )
        canonical = normalize_newlines(blob)
        canonical_digest = hashlib.sha256(canonical).hexdigest()
        materialized_digest = hashlib.sha256(
            canonical.replace(b"\n", b"\r\n")
        ).hexdigest()
        if expected not in {canonical_digest, materialized_digest}:
            mismatches.append(
                {
                    "path": relative,
                    "status": "SEALED_REPRESENTATION_MISMATCH",
                    "expected": expected,
                    "canonical_lf": canonical_digest,
                    "materialized_crlf": materialized_digest,
                }
            )
            continue
        if normalize_newlines(checkout) != canonical:
            mismatches.append(
                {
                    "path": relative,
                    "status": "CHECKOUT_CONTENT_MISMATCH",
                    "expected": expected,
                    "actual": checkout_digest,
                }
            )
            continue
        representation = (
            "sealed_canonical_lf"
            if expected == canonical_digest
            else "sealed_materialized_crlf"
        )
        representations[representation] += 1
        verified[relative] = expected

    aggregate = hashlib.sha256()
    for relative, digest in sorted(verified.items()):
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\0")

    excluded = {"scoring_surface.json", "mechanism_seal.json"}
    observed_files = {
        path.relative_to(run_root).as_posix()
        for path in run_root.rglob("*")
        if path.is_file() and path.name not in excluded
    }
    extras = sorted(observed_files - set(expected_files))
    missing = sorted(set(expected_files) - observed_files)
    aggregate_digest = aggregate.hexdigest()
    status = (
        "PASS"
        if not mismatches
        and not extras
        and not missing
        and len(verified) == int(seal["mechanism_file_count"])
        and aggregate_digest == seal["aggregate_sha256"]
        else "FAIL"
    )
    return {
        "status": status,
        "seal_status": seal["status"],
        "mechanism_file_count": len(verified),
        "expected_file_count": int(seal["mechanism_file_count"]),
        "aggregate_sha256": aggregate_digest,
        "expected_aggregate_sha256": seal["aggregate_sha256"],
        "representations": representations,
        "mismatches": mismatches,
        "extra_files": extras,
        "missing_files": missing,
    }


def normalize_newlines(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
