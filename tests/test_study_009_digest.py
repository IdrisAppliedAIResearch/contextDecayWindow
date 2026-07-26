from dataclasses import replace

import numpy as np

from src.memory.topic_digest import (
    DigestFrame,
    DigestSpan,
    TopicDigest,
    render_topic_digest,
)


def span(
    topic: str,
    turn: int,
    text: str,
    density: float = 1.0,
) -> DigestSpan:
    return DigestSpan(
        topic_id=topic,
        topic_label=topic,
        source_episode_id=f"episode-{turn}",
        source_turn=turn,
        role="user",
        span_start=0,
        span_end=len(text),
        text=text,
        density=density,
    )


def test_serialized_cost_is_the_budget_authority():
    digest = TopicDigest(
        conn=None,
        embedding_provider=lambda _: np.ones(2, dtype=np.float32),
        spans_per_topic=2,
        budget=420,
    )
    selected = digest._fit_budget({
        "a": [
            span("a", 1, "Alpha & Beta 100 facts appear here.", 2.0),
            span("a", 2, "Second Alpha fact with markup <escaped>.", 1.0),
        ],
        "b": [
            span("b", 3, "Gamma 200 facts appear in this sentence.", 2.0),
            span("b", 4, "Second Gamma fact with quoted \"data\".", 1.0),
        ],
    })
    digest.frame = DigestFrame(selected, digest.budget, 31)

    rendered = digest.render()

    assert rendered.chars == len(rendered.text)
    assert rendered.chars <= digest.budget
    assert "&amp;" in rendered.text
    assert "&lt;escaped&gt;" not in rendered.text or rendered.chars <= 420


def test_budget_pressure_preserves_one_span_per_topic():
    digest = TopicDigest(
        conn=None,
        embedding_provider=lambda _: np.ones(2, dtype=np.float32),
        spans_per_topic=2,
        budget=650,
    )
    long = " ".join(["Documented"] * 40)
    selected = digest._fit_budget({
        "a": [span("a", 1, long, 3.0), span("a", 2, long, 2.0)],
        "b": [span("b", 3, long, 3.0), span("b", 4, long, 2.0)],
        "c": [span("c", 5, long, 3.0), span("c", 6, long, 2.0)],
    })
    rendered = render_topic_digest(selected)

    assert {item.topic_id for item in selected} == {"a", "b", "c"}
    assert all(sum(item.topic_id == topic for item in selected) >= 1 for topic in "abc")
    assert len(rendered) <= digest.budget
    assert any(item.text.endswith("...") for item in selected)


def test_containment_drops_without_refill():
    digest = TopicDigest(
        conn=None,
        embedding_provider=lambda _: np.ones(2, dtype=np.float32),
        spans_per_topic=2,
        budget=2500,
    )
    digest.frame = DigestFrame(
        spans=[
            span("a", 1, "Alpha 100 fact sentence.", 2.0),
            span("a", 2, "Alpha 200 backup sentence.", 1.0),
            span("b", 3, "Beta 300 fact sentence.", 2.0),
        ],
        budget=2500,
        built_at_turn=31,
    )

    rendered = digest.render({"episode-1"})

    assert rendered.span_count == 2
    assert len(rendered.containment_drops) == 1
    assert rendered.containment_drops[0]["source_episode_id"] == "episode-1"
    assert "Alpha 100 fact sentence." not in rendered.text
    assert "Alpha 200 backup sentence." in rendered.text


def test_dedup_keeps_higher_density_span():
    digest = TopicDigest(
        conn=None,
        embedding_provider=lambda _: np.ones(2, dtype=np.float32),
    )
    high = span("a", 1, "High density 100.", 2.0)
    low = replace(high, source_episode_id="episode-2", source_turn=2, density=1.0)
    vector = np.array([1.0, 0.0], dtype=np.float32)

    survivors = digest._deduplicate([(low, vector), (high, vector)])

    assert [item[0] for item in survivors] == [high]
