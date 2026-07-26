"""Structural leakage audit for Study 008 retrieval modules."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


FORBIDDEN_LITERALS = (
    "q_facts_key.md",
    "rubric_filled.md",
    "q14_criteria.md",
    "rubric_scores.json",
    "study_008_results.json",
)

DEFAULT_SCAN_DIRS = (
    Path("src/memory"),
    Path("src/db"),
    Path("src/embeddings"),
)

DEFAULT_IMPORT_ROOTS = (
    Path("src/memory/retrieval_engine.py"),
    Path("src/memory/retrieval_budget.py"),
    Path("src/memory/arbitration.py"),
    Path("src/memory/context_builder.py"),
    Path("src/memory/distilled_ltm_store.py"),
)


@dataclass(frozen=True)
class LeakageViolation:
    detector: str
    path: str
    detail: str


@dataclass(frozen=True)
class LeakageAudit:
    literal_violations: tuple[LeakageViolation, ...]
    import_violations: tuple[LeakageViolation, ...]
    scanned_files: tuple[str, ...]
    import_closure: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.literal_violations and not self.import_violations


def _python_files(repo: Path, directories: tuple[Path, ...]) -> list[Path]:
    files: set[Path] = set()
    for directory in directories:
        root = repo / directory
        if root.exists():
            files.update(path for path in root.rglob("*.py") if path.is_file())
    return sorted(files)


def _forbidden_in_text(text: str) -> list[str]:
    lowered = text.casefold()
    return [
        literal
        for literal in FORBIDDEN_LITERALS
        if literal.casefold() in lowered
    ]


def literal_scan(
    repo: Path,
    directories: tuple[Path, ...] = DEFAULT_SCAN_DIRS,
) -> tuple[list[LeakageViolation], list[Path]]:
    files = _python_files(repo, directories)
    violations = []
    for path in files:
        hits = _forbidden_in_text(path.read_text(encoding="utf-8"))
        for hit in hits:
            violations.append(
                LeakageViolation(
                    detector="literal",
                    path=path.relative_to(repo).as_posix(),
                    detail=hit,
                )
            )
    return violations, files


def _module_index(repo: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    src = repo / "src"
    for path in src.rglob("*.py"):
        relative = path.relative_to(repo).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        index[".".join(parts)] = path
    return index


def _local_imports(path: Path, module_index: dict[str, Path]) -> list[Path]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[Path] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [
                f"{node.module}.{alias.name}"
                for alias in node.names
                if alias.name != "*"
            ]
            names.append(node.module)
        for name in names:
            candidate = name
            while candidate:
                resolved = module_index.get(candidate)
                if resolved is not None:
                    imports.add(resolved)
                    break
                candidate = candidate.rpartition(".")[0]
    return sorted(imports)


def import_closure_scan(
    repo: Path,
    roots: tuple[Path, ...] = DEFAULT_IMPORT_ROOTS,
) -> tuple[list[LeakageViolation], list[Path]]:
    module_index = _module_index(repo)
    pending = [repo / root for root in roots]
    visited: set[Path] = set()
    violations = []

    while pending:
        path = pending.pop()
        if path in visited or not path.exists():
            continue
        visited.add(path)
        text = path.read_text(encoding="utf-8")
        for hit in _forbidden_in_text(text):
            violations.append(
                LeakageViolation(
                    detector="import-closure",
                    path=path.relative_to(repo).as_posix(),
                    detail=hit,
                )
            )
        pending.extend(
            imported
            for imported in _local_imports(path, module_index)
            if imported not in visited
        )

    return violations, sorted(visited)


def run_leakage_audit(
    repo: Path,
    scan_dirs: tuple[Path, ...] = DEFAULT_SCAN_DIRS,
    import_roots: tuple[Path, ...] = DEFAULT_IMPORT_ROOTS,
) -> LeakageAudit:
    literal_violations, scanned = literal_scan(repo, scan_dirs)
    import_violations, closure = import_closure_scan(repo, import_roots)
    return LeakageAudit(
        literal_violations=tuple(literal_violations),
        import_violations=tuple(import_violations),
        scanned_files=tuple(path.relative_to(repo).as_posix() for path in scanned),
        import_closure=tuple(path.relative_to(repo).as_posix() for path in closure),
    )
