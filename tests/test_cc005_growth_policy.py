"""CC-005: the growth policy is stated, and nothing was built.

Part 3 ships documentation and measurement. Its deliverables are therefore
mostly assertions about what the package does *not* contain, plus checks
that the numbers in the README trace to a committed artifact.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))

import episodic  # noqa: E402
from episodic import EpisodicConfig  # noqa: E402
from episodic._errors import EpisodicError  # noqa: E402

PACKAGE_ROOT = REPO_ROOT / "episodic" / "src" / "episodic"
README = REPO_ROOT / "episodic" / "README.md"
MEASUREMENT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "deployment_closeout"
    / "artifacts"
    / "cc005"
    / "growth_measurement.json"
)


@pytest.fixture(scope="module")
def measurement():
    if not MEASUREMENT.exists():
        pytest.skip("CC-005 measurement artifact is not present")
    return json.loads(MEASUREMENT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def readme():
    return README.read_text(encoding="utf-8")


class TestNoEvictionShipped:
    """Section 3.5: no eviction implementation in v0."""

    def test_no_eviction_api_is_exported(self):
        exported = set(episodic.__all__)
        for name in exported:
            assert "evict" not in name.lower()
            assert "prune" not in name.lower()
            assert "expire" not in name.lower()

    def test_the_store_has_no_eviction_method(self):
        from episodic import EpisodeStore

        for name in dir(EpisodeStore):
            assert "evict" not in name.lower()
            assert "prune" not in name.lower()

    def test_no_module_defines_an_eviction_function(self):
        for path in sorted(PACKAGE_ROOT.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            for marker in ("def evict", "def prune", "def expire"):
                assert marker not in source, f"{path.name} defines {marker}"

    def test_the_store_is_still_append_only(self):
        for path in sorted(PACKAGE_ROOT.glob("*.py")):
            source = path.read_text(encoding="utf-8").upper()
            assert "DELETE FROM EPISODES" not in source
            assert "DROP TABLE EPISODES" not in source


class TestUnsafePrefixRetained:
    """Section 3.5: the `unsafe_` prefix stays on any trimming API."""

    def test_the_trimming_knob_keeps_its_prefix(self):
        assert hasattr(EpisodicConfig(), "unsafe_cosine_top_n")

    def test_the_trimming_policy_is_not_the_default(self):
        assert EpisodicConfig().candidate_policy == "full_store"

    def test_the_policy_name_carries_the_warning(self):
        config = EpisodicConfig(candidate_policy="unsafe_cosine_top_n")
        assert config.candidate_policy.startswith("unsafe_")

    def test_an_unnamed_trimming_policy_is_refused(self):
        with pytest.raises(EpisodicError):
            EpisodicConfig(candidate_policy="cosine_top_n")

    def test_the_dr002_finding_travels_with_the_code(self):
        from episodic import _context

        doc = _context._candidate_pool.__doc__
        assert "DR-002" in doc
        assert "domain" in doc


class TestMeasurementsAreReal:
    """The README's numbers have to trace to the committed artifact."""

    def test_disk_growth_is_measured_not_estimated(self, measurement):
        disk = measurement["disk"]
        assert disk["measured_to_turns"] == 1_000
        assert 3_000 < disk["marginal_bytes_per_turn"] < 8_000
        assert disk["embedding_bytes_per_turn"] == 4_096

    def test_latency_is_measured_to_the_largest_store(self, measurement):
        latency = measurement["latency"]
        assert latency["measured_to_candidates"] == 1_000
        assert latency["embedding_excluded"] is True
        assert latency["measured_max_ms"] > 0

    def test_projections_are_labelled_as_projections(self, measurement):
        latency = measurement["latency"]
        key = "projections_labelled_as_projections"
        assert key in latency
        for horizon in latency[key]:
            assert int(horizon) > latency["measured_to_candidates"]

    def test_clustering_is_the_dominant_cost(self, measurement):
        components = measurement["components"]
        assert components["cluster_share_at_max"] > 0.6
        assert components["dominant_stage"] == "cluster_setup"

    def test_per_candidate_cost_is_not_flat_beyond_dr002(self, measurement):
        """The correction ERRATA records: flat to 119, rising after."""
        rows = measurement["latency"]["rows"]
        smallest = rows[0]["us_per_candidate"]
        largest = rows[-1]["us_per_candidate"]
        assert largest > smallest * 1.5

    def test_context_is_recorded_as_bounded(self, measurement):
        assert measurement["context_window"]["bounded"] is True
        assert measurement["context_window"]["source"] == "CC-003 G-E0"


class TestReadmeStatesThePolicy:
    """Section 3.3: stating the policy is the deliverable."""

    def test_the_retention_policy_is_stated(self, readme):
        assert "unbounded retention" in readme.lower()
        assert "evicts nothing" in readme.lower()

    def test_disk_growth_is_documented(self, readme):
        assert "bytes per turn" in readme

    def test_the_horizon_is_stated_with_a_threshold(self, readme):
        assert "horizon" in readme.lower()
        assert "10,000" in readme

    def test_projections_are_marked_as_projections(self, readme):
        assert "projections from the fitted exponent, not measurements" in readme

    def test_unsafe_trimming_is_documented_with_its_artifact(self, readme):
        assert "DR-002" in readme
        assert "unsafe_cosine_top_n" in readme
        assert "4 of the 5" in readme

    def test_the_errata_correction_is_pointed_at(self, readme):
        assert "ERRATA.md" in readme
        assert "20–119" in readme or "20-119" in readme
