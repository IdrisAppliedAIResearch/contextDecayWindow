from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPOSITORY_ROOT / "scripts" / "generate_study_003_figures.py"
FIGURE_ROOT = REPOSITORY_ROOT / "experiments" / "study_003" / "figures"
EXPECTED_FIGURES = {
    "study-overview.svg",
    "memory-architecture.svg",
    "confirmatory-outcomes.svg",
    "topic-context-trajectories.svg",
    "ltm-promotion-outcomes.svg",
    "filter-score-distributions.svg",
}
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"


def test_study_003_figures_match_canonical_artifacts():
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_study_003_figures_are_accessible_svg_documents():
    paths = set(FIGURE_ROOT.glob("*.svg"))
    assert {path.name for path in paths} == EXPECTED_FIGURES
    for path in paths:
        root = ElementTree.parse(path).getroot()
        assert root.tag == f"{SVG_NAMESPACE}svg"
        title = root.find(f"{SVG_NAMESPACE}title")
        description = root.find(f"{SVG_NAMESPACE}desc")
        assert title is not None and title.text
        assert description is not None and description.text
