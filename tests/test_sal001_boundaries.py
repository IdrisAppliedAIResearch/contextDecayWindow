from __future__ import annotations

import ast
from pathlib import Path

from src.analysis.sal001_preflight import FORBIDDEN_SCORE_IMPORTS, _unauthorized_keys
from src.analysis.sal001_score import validate_manifest


def test_score_module_has_no_forbidden_import_boundary() -> None:
    path = Path("src/analysis/sal001_score.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not (imports & FORBIDDEN_SCORE_IMPORTS)


def test_valid_label_free_manifest_has_no_forbidden_keys() -> None:
    manifest = {
        "schema": "sal001-label-free-scorer-manifest-v1",
        "dataset_sha256": "0" * 64,
        "sessions": [
            {
                "session_sha256": "1" * 64,
                "exchange_count": 1,
                "exchanges": [
                    {
                        "exchange_index": 0,
                        "content_sha256": "2" * 64,
                        "user": "hello",
                        "assistant": "hi",
                    }
                ],
            }
        ],
    }
    assert len(validate_manifest(manifest)) == 1
    assert _unauthorized_keys(manifest) == []


def test_planted_nested_label_key_is_detected() -> None:
    assert _unauthorized_keys({"sessions": [{"labels": [False]}]}) == ["labels"]

