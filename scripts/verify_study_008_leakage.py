"""Run and record the Study 008 retrieval leakage audit."""

from __future__ import annotations

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.analysis.study_008_leakage import run_leakage_audit  # noqa: E402


OUTPUT = REPO / "experiments/study_008/audits/leakage_audit.md"


def main() -> int:
    audit = run_leakage_audit(REPO)
    lines = [
        "# Study 008 — Retrieval Leakage Audit",
        "",
        "**Command:** `.venv/Scripts/python.exe scripts/verify_study_008_leakage.py`",
        f"**Verdict:** {'PASS' if audit.passed else 'FAIL'}",
        "",
        "## Literal scan",
        "",
        f"- Python files scanned: {len(audit.scanned_files)}",
        f"- Violations: {len(audit.literal_violations)}",
        "",
        "## Import-closure scan",
        "",
        f"- Modules in retrieval closure: {len(audit.import_closure)}",
        f"- Violations: {len(audit.import_violations)}",
        "",
        "## Retrieval import closure",
        "",
        *[f"- `{path}`" for path in audit.import_closure],
        "",
        "## Violations",
        "",
    ]
    violations = (*audit.literal_violations, *audit.import_violations)
    if violations:
        lines.extend(
            f"- `{item.detector}` `{item.path}`: `{item.detail}`"
            for item in violations
        )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "The test suite also plants a transitive test-only violation and",
            "requires both detectors to reject it.",
            "",
        ]
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Study 008 leakage audit: {'PASS' if audit.passed else 'FAIL'}")
    print(f"Literal files scanned: {len(audit.scanned_files)}")
    print(f"Import closure modules: {len(audit.import_closure)}")
    print(f"Report: {OUTPUT.relative_to(REPO)}")
    return 0 if audit.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
