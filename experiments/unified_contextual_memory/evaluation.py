"""Measurement-only scoring, statistics, and fail-closed gates."""
import json
from pathlib import Path
import re
import subprocess
import numpy as np
from prepare import ROOT, P, sha


def verdict(text):
    matches = list(re.finditer(r"(?im)^VERDICT:\s*(CORRECT|INCORRECT)\s*$", text))
    if not matches:
        raise ValueError("Missing final verdict")
    last = matches[-1]
    reason = re.search(r"(?m)^REASON:\s*(\S.*)$", text[last.end():])
    if not reason:
        raise ValueError("Final verdict lacks reason")
    return last.group(1).upper() == "CORRECT", reason.group(1)


def outside_reasoning(text):
    """Measurement fixture only; actual native-off outputs reject reasoning tags."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


def committed(path):
    relative = str(Path(path).resolve().relative_to(ROOT))
    subprocess.run(["git", "ls-files", "--error-unmatch", relative], cwd=ROOT,
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    changes = subprocess.check_output(["git", "status", "--porcelain", "--", relative], cwd=ROOT, text=True)
    if changes.strip():
        raise ValueError(f"Uncommitted artifact: {relative}")


def gate(base=P):
    registration = base / "PRE_REGISTRATION.md"
    preflight = base / "artifacts/preflight.json"
    for path in (registration, preflight):
        if not path.is_file():
            raise ValueError("Registration/preflight missing; generation forbidden")
        committed(path)
    manifest = json.loads(preflight.read_text(encoding="utf-8"))
    if manifest["status"] != "PASS":
        raise ValueError("Preflight has not passed")
    for path, expected in manifest["hashes"].items():
        actual = ROOT / path
        committed(actual)
        if sha(actual) != expected:
            raise ValueError(f"Frozen input drift: {path}")
    return manifest


def paired(rows):
    """Occurrence-weighted difference; paired conversation-cluster bootstrap."""
    conversations = sorted({r["conversation"] for r in rows})
    sums = np.array([sum(int(r["C1"])-int(r["C0"]) for r in rows if r["conversation"]==c) for c in conversations])
    counts = np.array([sum(r["conversation"]==c for r in rows) for c in conversations])
    rng = np.random.default_rng(70107)
    draws = rng.integers(0, len(conversations), size=(20000, len(conversations)))
    boot = sums[draws].sum(axis=1)/counts[draws].sum(axis=1)
    lo, hi = np.quantile(boot, [.025,.975])
    return dict(n=len(rows), C0=sum(r["C0"] for r in rows), C1=sum(r["C1"] for r in rows),
                difference=float(sums.sum()/counts.sum()), ci95=[float(lo),float(hi)],
                gains=sum(r["C1"] and not r["C0"] for r in rows),
                losses=sum(r["C0"] and not r["C1"] for r in rows))


def disposition(result, strata, selective):
    safe = all(r["difference"] >= -.03 for r in strata.values())
    if selective and safe and result["difference"] >= .02 and result["ci95"][0] > 0:
        return "WORKS_ON_EXPOSED_LOCOMO"
    if selective and safe and result["difference"] >= .01:
        return "WEAK_SIGNAL_ON_EXPOSED_LOCOMO"
    return "NO_QUALIFYING_GAIN"
