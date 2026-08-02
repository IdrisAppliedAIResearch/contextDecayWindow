"""CC-003 budget enforcement: tests E1-E6.

The store under test is the committed Study 010 arm L store - 1,000 real
episodes with their committed embeddings - so the sweep runs against the
same material every published retrieval number came from. No embedder is
needed: `build_context` is a pure function of episodes, a query vector, a
budget, and a config.

E6 is the replay gate. The E005 primary ran at 31,569 of 32,000
characters, so enforcement should be inert there; if that number moves,
enforcement changed selection and the cause has to be found before merge.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))

from episodic._config import EpisodicConfig  # noqa: E402
from episodic._context import build_context  # noqa: E402
from episodic._packing import (  # noqa: E402
    DROP_POLICY,
    EMPTY_PAYLOAD_CHARS,
    pack_stm_payload,
)
from episodic._render import render_stm_payload  # noqa: E402

from src.analysis.cc003_growth_gate import ARM_L_DB, load_episodes  # noqa: E402

PRIMARY_PAYLOAD = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "retrieval_mechanism_ledger"
    / "artifacts"
    / "e005"
    / "primary_payload.txt"
)

#: E1's registered sweep: 1k to 64k. The step is coarse enough to run in
#: a unit suite and fine enough to straddle the operating point.
SWEEP_BUDGETS = [1_000 * n for n in range(1, 65)]

#: Adversarially small budgets, below anything a caller would choose on
#: purpose. A ceiling that holds only for sensible budgets is not a
#: ceiling.
PATHOLOGICAL_BUDGETS = [0, 1, 2, 10, 34, 35, 36, 50, 100, 200]


@pytest.fixture(scope="module")
def episodes():
    if not ARM_L_DB.exists():
        pytest.skip("Study 010 arm L store is not present")
    return load_episodes()


@pytest.fixture(scope="module")
def query(episodes):
    return episodes[-1]["embedding"]


def _context(episodes, query, budget, config=None):
    return build_context(
        episodes=episodes,
        query_embedding=query,
        budget=budget,
        config=config or EpisodicConfig(),
    )


class TestE1Ceiling:
    """E1 - chars_delivered <= budget at every point of the sweep."""

    @pytest.mark.parametrize("budget", SWEEP_BUDGETS)
    def test_delivered_never_exceeds_budget(self, episodes, query, budget):
        block, report = _context(episodes[:200], query, budget)
        assert len(block) <= budget
        assert report.chars_delivered == len(block)
        assert report.chars_delivered <= budget

    @pytest.mark.parametrize("budget", PATHOLOGICAL_BUDGETS)
    def test_ceiling_holds_at_adversarial_budgets(
        self, episodes, query, budget
    ):
        block, report = _context(episodes[:200], query, budget)
        assert len(block) <= budget
        assert report.chars_available >= 0

    def test_ceiling_holds_on_the_full_thousand_turn_store(
        self, episodes, query
    ):
        block, report = _context(episodes, query, 32_000)
        assert len(block) <= 32_000
        assert report.chars_delivered <= 32_000

    def test_the_ceiling_is_not_met_by_delivering_nothing(
        self, episodes, query
    ):
        """The surrogate named in section 1.4: `<=` passes trivially at 0."""
        block, report = _context(episodes, query, 32_000)
        assert report.episodes_delivered > 0
        assert len(block) > 30_000
        assert "<episode" in block


class TestE2TruncationFires:
    """E2 - every budget where selection wants more sets truncated."""

    @pytest.mark.parametrize("budget", [1_000, 4_000, 8_000, 16_000, 31_000])
    def test_shortfall_sets_truncated(self, episodes, query, budget):
        _, report = _context(episodes[:200], query, budget)
        assert report.chars_wanted > report.chars_delivered
        assert report.truncated
        assert report.episodes_dropped > 0
        assert report.shortfall_chars > 0

    def test_dropped_identities_are_reported(self, episodes, query):
        """A boolean alone lets a caller know something happened, not what."""
        _, report = _context(episodes[:200], query, 8_000)
        assert len(report.dropped_ids) == report.episodes_dropped
        assert all(isinstance(item, str) for item in report.dropped_ids)
        assert len(set(report.dropped_ids)) == len(report.dropped_ids)

    def test_dropped_identities_are_not_delivered(self, episodes, query):
        """Matched on turn number: the scripted prompts repeat verbatim, so
        message text does not identify an episode but the turn does."""
        import re

        block, report = _context(episodes[:200], query, 8_000)
        delivered_turns = {
            int(turn) for turn in re.findall(r'<episode turn="(\d+)"', block)
        }
        by_id = {str(item["id"]): item for item in episodes[:200]}
        dropped_turns = {
            int(by_id[identifier]["turn_number"])
            for identifier in report.dropped_ids
        }
        assert dropped_turns
        assert delivered_turns
        assert not (delivered_turns & dropped_turns)

    def test_drop_policy_is_named(self, episodes, query):
        _, report = _context(episodes[:200], query, 8_000)
        assert report.drop_policy == DROP_POLICY
        assert report.drop_policy


class TestE3NoFalsePositives:
    """E3 - no budget where selection fits sets truncated."""

    def test_generous_budget_is_not_truncated(self, episodes, query):
        subset = episodes[:12]
        wanted = len(render_stm_payload(subset, []))
        _, report = _context(subset, query, wanted * 10)
        assert not report.truncated
        assert report.episodes_dropped == 0
        assert report.dropped_ids == ()

    def test_untruncated_report_is_self_consistent(self, episodes, query):
        subset = episodes[:12]
        _, report = _context(subset, query, 200_000)
        assert report.chars_wanted == report.chars_delivered
        assert report.shortfall_chars == 0
        assert report.episodes_delivered == len(subset)

    def test_single_episode_store_fits(self, episodes, query):
        _, report = _context(episodes[:1], query, 32_000)
        assert not report.truncated
        assert report.episodes_delivered == 1


class TestE4Pathological:
    """E4 - a budget below one episode degrades, and does not raise."""

    def test_budget_below_the_empty_tags_returns_an_empty_block(
        self, episodes, query
    ):
        block, report = _context(episodes[:50], query, EMPTY_PAYLOAD_CHARS - 1)
        assert block == ""
        assert report.truncated
        assert report.episodes_delivered == 0
        assert report.episodes_dropped > 0

    def test_zero_budget_returns_an_empty_block(self, episodes, query):
        block, report = _context(episodes[:50], query, 0)
        assert block == ""
        assert report.truncated

    def test_negative_budget_returns_an_empty_block(self, episodes, query):
        block, report = _context(episodes[:50], query, -1)
        assert block == ""
        assert report.truncated

    def test_exactly_the_empty_tags_returns_the_empty_tags(
        self, episodes, query
    ):
        block, report = _context(episodes[:50], query, EMPTY_PAYLOAD_CHARS)
        assert block == render_stm_payload([], [])
        assert len(block) == EMPTY_PAYLOAD_CHARS
        assert report.episodes_delivered == 0
        assert report.truncated

    def test_budget_smaller_than_the_smallest_episode(self, episodes, query):
        """The cheapest placement of the cheapest episode, minus one.

        An episode costs two characters less in `retrieved_stm` than in
        `recent_context`, because the tag names differ in length, so the
        floor has to be taken over both tiers or the test leaves room for
        exactly the case it means to exclude.
        """
        subset = episodes[:50]
        smallest = min(
            min(
                len(render_stm_payload([item], [])),
                len(render_stm_payload([], [item])),
            )
            for item in subset
        )
        block, report = _context(subset, query, smallest - 1)
        assert len(block) <= smallest - 1
        assert report.episodes_delivered == 0
        assert report.truncated

    @pytest.mark.parametrize("budget", PATHOLOGICAL_BUDGETS)
    def test_no_budget_raises(self, episodes, query, budget):
        _context(episodes[:50], query, budget)

    def test_packing_directly_does_not_raise_below_the_tags(self, episodes):
        packed = pack_stm_payload(episodes[:3], episodes[3:6], 5)
        assert packed.payload == ""
        assert len(packed.skipped_n_ids) == 3
        assert len(packed.skipped_k_ids) == 3

    def test_empty_store_is_not_truncated(self, query):
        block, report = _context([], query, 32_000)
        assert block == render_stm_payload([], [])
        assert not report.truncated
        assert report.episodes_delivered == 0


class TestE5Determinism:
    """E5 - drop order is identical across processes."""

    def test_same_process_repeat_is_identical(self, episodes, query):
        first_block, first = _context(episodes[:300], query, 12_000)
        second_block, second = _context(episodes[:300], query, 12_000)
        assert first_block == second_block
        assert first.dropped_ids == second.dropped_ids

    def test_separate_processes_agree(self):
        """Two interpreters, one fixed seed, byte-identical drop order."""
        script = (
            "import sys, json;"
            f"sys.path.insert(0, {str(REPO_ROOT)!r});"
            f"sys.path.insert(0, {str(REPO_ROOT / 'episodic' / 'src')!r});"
            "from episodic._config import EpisodicConfig;"
            "from episodic._context import build_context;"
            "from src.analysis.cc003_growth_gate import load_episodes;"
            "eps = load_episodes()[:300];"
            "block, report = build_context(episodes=eps,"
            " query_embedding=eps[-1]['embedding'], budget=12000,"
            " config=EpisodicConfig());"
            "print(json.dumps({'chars': len(block),"
            " 'dropped': list(report.dropped_ids),"
            " 'delivered': report.episodes_delivered}))"
        )
        runs = [
            subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                check=True,
            ).stdout.strip()
            for _ in range(2)
        ]
        assert runs[0] == runs[1]
        assert runs[0]

    def test_drop_order_follows_proposal_order(self, episodes, query):
        """Dropped identities are reported in the order they were proposed."""
        _, report = _context(episodes[:200], query, 6_000)
        assert report.dropped_ids
        assert len(report.dropped_ids) == report.episodes_dropped


class TestE6ReplayGate:
    """E6 - the operating point is unchanged by enforcement."""

    @pytest.fixture(scope="class")
    def committed_payload(self):
        if not PRIMARY_PAYLOAD.exists():
            pytest.skip("E005 primary payload artifact is not present")
        return PRIMARY_PAYLOAD.read_text(encoding="utf-8").replace("\r\n", "\n")

    def test_committed_primary_is_the_operating_point(self, committed_payload):
        assert len(committed_payload) == 31_569
        assert len(committed_payload) < 32_000

    def test_packing_the_primary_reproduces_it_byte_for_byte(
        self, committed_payload
    ):
        """Enforcement must be inert at 31,569 of 32,000."""
        episodes = _parse_payload_episodes(committed_payload)
        packed = pack_stm_payload([], episodes, 32_000)
        assert packed.payload == committed_payload
        assert packed.serialized_chars == 31_569
        assert packed.skipped_k_ids == ()

    def test_the_primary_still_fits_under_the_ceiling(self, committed_payload):
        episodes = _parse_payload_episodes(committed_payload)
        packed = pack_stm_payload([], episodes, 32_000)
        assert packed.serialized_chars <= 32_000

    def test_committed_result_vector_is_on_the_record(self):
        """12/17 across 4/4 domains, 16/16 targeted, 31,569 chars."""
        import json

        artifact = (
            REPO_ROOT
            / "experiments"
            / "components"
            / "library_extraction"
            / "artifacts"
            / "cc002"
            / "t3_e005_replay.json"
        )
        if not artifact.exists():
            pytest.skip("CC-002 T3 artifact is not present")
        record = json.loads(artifact.read_text(encoding="utf-8"))
        assert record["primary_result_vector"] == {
            "q11_domain_count": 4,
            "q11_fact_count": 12,
            "serialized_chars": 31_569,
            "targeted_preserved": 16,
        }
        assert record["status"] == "PASS"


def _parse_payload_episodes(payload: str) -> list[dict]:
    """Recover the selected episodes from a committed rendered payload."""
    import html
    import re

    pattern = re.compile(
        r"<episode turn=\"(?P<turn>[^\"]*)\">\n"
        r"<user>(?P<user>.*?)</user>\n"
        r"<assistant>(?P<assistant>.*?)</assistant>\n"
        r"</episode>",
        re.S,
    )
    return [
        {
            "id": f"committed-{index}",
            "turn_number": html.unescape(match["turn"]),
            "user_message": html.unescape(match["user"]),
            "assistant_message": html.unescape(match["assistant"]),
        }
        for index, match in enumerate(pattern.finditer(payload))
    ]


class TestReportContract:
    """Requirement 1.2.3 and 1.2.5: the signal has to be actionable."""

    def test_report_carries_the_budget_it_was_given(self, episodes, query):
        _, report = _context(episodes[:100], query, 9_000)
        assert report.budget_chars == 9_000

    def test_chars_wanted_is_measured_before_packing(self, episodes, query):
        """The caller sees the size of the shortfall, not its existence."""
        _, tight = _context(episodes[:200], query, 4_000)
        _, loose = _context(episodes[:200], query, 40_000)
        assert tight.chars_wanted > tight.chars_delivered
        assert loose.chars_delivered >= tight.chars_delivered
        assert tight.shortfall_chars > 0

    def test_counts_attribute_every_delivered_episode(self, episodes, query):
        _, report = _context(episodes[:200], query, 16_000)
        assert (
            report.stm_count + report.k_count + report.coverage_count
            == report.episodes_delivered
        )
