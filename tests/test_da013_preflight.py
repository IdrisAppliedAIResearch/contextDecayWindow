from pathlib import Path

from analysis.da013_preflight import BlindEpisode, BlindQuestion, _edges, identity
from analysis.nf005_mechanism import Candidate


def _episode(session: str, session_order: int, episode_order: int) -> BlindEpisode:
    text = f"User: u{episode_order}\nAssistant: a{episode_order}"
    candidate = Candidate(
        identity=identity(session, str(episode_order)),
        parent_index=episode_order,
        session_order=session_order,
        episode_order=episode_order,
        turn_offset=-1,
        text=text,
        chars=len(text),
    )
    return BlindEpisode(candidate, session, ({"speaker": "User", "text": f"u{episode_order}"}, {"speaker": "Assistant", "text": f"a{episode_order}"}))


def test_temporal_edges_use_prior_then_next_and_deduplicate() -> None:
    episodes = tuple(_episode("s", 0, index) for index in range(4))
    record = BlindQuestion("q", "type", "question", episodes)
    direct = frozenset((episodes[1].candidate.identity, episodes[2].candidate.identity))
    edges = _edges(record, (1, 2, 0, 3), direct)
    assert [(row["seed_rank"], row["direction"]) for row in edges] == [
        (1, -1),
        (2, 1),
    ]
    assert len({row["neighbor_id"] for row in edges}) == len(edges)


def test_source_contains_no_evidence_field_names() -> None:
    source = Path("src/analysis/da013_preflight.py").read_text(encoding="utf-8").lower()
    assert "has_" + "answer" not in source
    assert "target_" + "turn" not in source
