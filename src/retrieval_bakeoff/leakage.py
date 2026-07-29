from __future__ import annotations

import ast
import builtins
import io
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import REPO_ROOT


FORBIDDEN_FRAGMENTS = (
    "answer_key",
    "overlap_matrix",
    "rubric",
    "q_facts_key",
)


class LeakageViolation(RuntimeError):
    pass


def scan_source(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations: set[str] = set()
    for node in ast.walk(tree):
        values: list[str] = []
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.append(node.value)
        elif isinstance(node, ast.Import):
            values.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                values.append(node.module)
            values.extend(alias.name for alias in node.names)
        for value in values:
            lowered = value.casefold()
            for fragment in FORBIDDEN_FRAGMENTS:
                if fragment in lowered:
                    violations.add(f"{path}:{getattr(node, 'lineno', 0)}:{fragment}")
    return sorted(violations)


def audit_import_graph(entry_paths: list[Path]) -> dict:
    pending = [path.resolve() for path in entry_paths]
    visited: set[Path] = set()
    violations: list[str] = []
    edges: list[tuple[str, str]] = []
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        violations.extend(scan_source(path))
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_name = _module_name(path)
        for imported in _imports(tree, module_name):
            target = _module_path(imported)
            if target is None:
                continue
            edges.append(
                (
                    str(path.relative_to(REPO_ROOT)),
                    str(target.relative_to(REPO_ROOT)),
                )
            )
            if target not in visited:
                pending.append(target)
    if violations:
        raise LeakageViolation(
            "Mechanism import graph contains forbidden references: "
            + "; ".join(violations)
        )
    return {
        "status": "PASS",
        "visited_modules": sorted(
            str(path.relative_to(REPO_ROOT)) for path in visited
        ),
        "edge_count": len(edges),
    }


@contextmanager
def guard_measurement_files() -> Iterator[list[str]]:
    observed: list[str] = []
    original_builtin_open = builtins.open
    original_io_open = io.open

    def guarded_open(file, *args, **kwargs):
        if isinstance(file, (str, bytes, Path)):
            display = str(file)
            observed.append(display)
            _assert_allowed_path(display)
        return original_io_open(file, *args, **kwargs)

    builtins.open = guarded_open
    io.open = guarded_open
    try:
        yield observed
    finally:
        builtins.open = original_builtin_open
        io.open = original_io_open


def assert_planted_violations(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    planted_module = directory / "planted_mechanism.py"
    planted_file = directory / "planted_answer_key.json"
    planted_module.write_text(
        'from src.retrieval_bakeoff.answer_key_reader import load\n',
        encoding="utf-8",
    )
    planted_file.write_text("{}\n", encoding="utf-8")

    module_rejected = bool(scan_source(planted_module))
    file_rejected = False
    try:
        with guard_measurement_files():
            planted_file.read_text(encoding="utf-8")
    except LeakageViolation:
        file_rejected = True
    if not module_rejected or not file_rejected:
        raise AssertionError("A planted leakage violation was not rejected")
    return {
        "status": "PASS",
        "planted_module_rejected": module_rejected,
        "planted_file_rejected": file_rejected,
    }


def _assert_allowed_path(path: str) -> None:
    lowered = path.casefold()
    matches = [fragment for fragment in FORBIDDEN_FRAGMENTS if fragment in lowered]
    if matches:
        raise LeakageViolation(
            f"Mechanism attempted to open a measurement artifact: {path}"
        )


def _module_name(path: Path) -> str:
    relative = path.resolve().relative_to(REPO_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _imports(tree: ast.AST, current_module: str) -> list[str]:
    imported: list[str] = []
    package = current_module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                relative = "." * node.level + (node.module or "")
                try:
                    base = __import__("importlib").util.resolve_name(
                        relative,
                        package,
                    )
                except (ImportError, ValueError):
                    continue
            else:
                base = node.module or ""
            imported.append(base)
            imported.extend(
                f"{base}.{alias.name}" if base else alias.name
                for alias in node.names
            )
    return imported


def _module_path(module_name: str) -> Path | None:
    if not module_name.startswith("src"):
        return None
    base = REPO_ROOT.joinpath(*module_name.split("."))
    module_path = base.with_suffix(".py")
    if module_path.is_file():
        return module_path.resolve()
    package_path = base / "__init__.py"
    if package_path.is_file():
        return package_path.resolve()
    return None
