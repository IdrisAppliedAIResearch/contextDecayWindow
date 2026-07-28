"""Atomic, auditable checkpoints for long Study 010 runs."""

import hashlib
import json
import os
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked_sizes(output_dir: Path) -> dict[str, int]:
    sizes = {}
    for path in output_dir.rglob("*"):
        if not path.is_file() or "checkpoints" in path.parts:
            continue
        if path.name == "study.db":
            continue
        sizes[path.relative_to(output_dir).as_posix()] = path.stat().st_size
    return sizes


def _payload_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_checkpoint(
    output_dir: Path,
    conn,
    turn: int,
    state: dict,
) -> Path:
    """Write a database backup, continuation state, and output byte ledger."""
    root = output_dir / "checkpoints"
    root.mkdir(parents=True, exist_ok=True)
    final = root / f"turn_{turn:04d}"
    staging = root / f".turn_{turn:04d}.tmp"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()

    db_path = staging / "study.db"
    backup = __import__("sqlite3").connect(str(db_path))
    try:
        conn.backup(backup)
    finally:
        backup.close()

    payload = {
        "turn": turn,
        "state": state,
        "output_sizes": _tracked_sizes(output_dir),
        "database_sha256": _sha256(db_path),
    }
    payload["payload_sha256"] = _payload_hash(payload)
    state_path = staging / "state.json"
    state_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if final.exists():
        shutil.rmtree(final)
    os.replace(staging, final)
    return final


def restore_checkpoint(output_dir: Path, checkpoint_dir: Path) -> dict:
    """Restore database/output boundaries and return continuation state."""
    payload = json.loads(
        (checkpoint_dir / "state.json").read_text(encoding="utf-8")
    )
    expected_payload_hash = payload.pop("payload_sha256")
    if _payload_hash(payload) != expected_payload_hash:
        raise ValueError("checkpoint state hash mismatch")
    payload["payload_sha256"] = expected_payload_hash
    db_source = checkpoint_dir / "study.db"
    if _sha256(db_source) != payload["database_sha256"]:
        raise ValueError("checkpoint database hash mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(db_source, output_dir / "study.db")
    expected = payload["output_sizes"]
    for relative, size in expected.items():
        path = output_dir / relative
        if not path.exists() or path.stat().st_size < size:
            raise ValueError(f"checkpoint output missing or short: {relative}")
        with path.open("r+b") as handle:
            handle.truncate(size)

    for path in output_dir.rglob("*"):
        if not path.is_file() or "checkpoints" in path.parts:
            continue
        relative = path.relative_to(output_dir).as_posix()
        if path.name != "study.db" and relative not in expected:
            path.unlink()
    return payload
