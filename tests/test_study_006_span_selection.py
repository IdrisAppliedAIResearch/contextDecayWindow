"""S6_003 — density + source-aware salience, and selection rewired to spans."""

import numpy as np
import pytest

from src.db.schema import init_db
from src.memory.distilled_ltm_store import (
    CONTENT_STATUS,
    NO_SALIENT_FACT_STATUS,
    assert_span_record_faithful,
    get_distilled_records,
)
from src.memory.span_dream_engine import (
    SOURCE_WEIGHTS,
    SpanCandidate,
    SpanDreamEngine,
    calculate_span_salience,
    source_weight,
)
from src.memory.span_segmenter import (
    ROLE_ASSISTANT,
    ROLE_USER,
    Span,
    segment_episode,
)


def make_span(
    text="The total main span is 847 meters.",
    role=ROLE_USER,
    word_count=7,
    named_entities=0,
    numeric_tokens=1,
    start=0,
    end=None,
    episode_id="episode-1",
    turn_number=3,
):
    return Span(
        text=text,
        start=start,
        end=len(text) if end is None else end,
        episode_id=episode_id,
        turn_number=turn_number,
        role=role,
        word_count=word_count,
        named_entities=named_entities,
        numeric_tokens=numeric_tokens,
        eligible=True,
    )


def candidate_from(span, embedding=None):
    base, density, salience = calculate_span_salience(span)
    return SpanCandidate(
        span=span,
        episode={"id": span.episode_id, "turn_number": span.turn_number},
        base=base,
        density=density,
        salience=salience,
        embedding=(
            np.array([1.0, 0.0], dtype=np.float32)
            if embedding is None
            else np.asarray(embedding, dtype=np.float32)
        ),
        source_episode_ids=[span.episode_id],
        source_turns=[span.turn_number],
    )


# --- S6-T-006: salience --------------------------------------------------


def test_salience_formula_components():
    span = make_span(word_count=10, named_entities=3, numeric_tokens=2)
    base, density, salience = calculate_span_salience(span)

    assert base == 3 + 2 * 2
    assert density == pytest.approx(7 / 10)
    assert salience == pytest.approx(7 / 10 * 1.5)


def test_numeric_tokens_carry_double_weight():
    entity_only = make_span(word_count=10, named_entities=2, numeric_tokens=0)
    numeric_only = make_span(word_count=10, named_entities=0, numeric_tokens=2)

    assert calculate_span_salience(entity_only)[0] == 2
    assert calculate_span_salience(numeric_only)[0] == 4


def test_user_span_outranks_identical_assistant_span_by_exactly_1_5x():
    user = make_span(role=ROLE_USER, word_count=10, named_entities=2, numeric_tokens=1)
    assistant = make_span(
        role=ROLE_ASSISTANT, word_count=10, named_entities=2, numeric_tokens=1
    )

    user_salience = calculate_span_salience(user)[2]
    assistant_salience = calculate_span_salience(assistant)[2]

    assert user_salience == pytest.approx(assistant_salience * 1.5)
    assert SOURCE_WEIGHTS[ROLE_USER] == 1.5
    assert SOURCE_WEIGHTS[ROLE_ASSISTANT] == 1.0


def test_unknown_role_defaults_to_neutral_weight():
    assert source_weight("conversation") == 1.0


def test_short_dense_plant_outranks_long_diffuse_span_with_higher_absolute_count():
    """The core correction, asserted directly.

    The decoy has a strictly higher absolute entity+numeric count - exactly the
    Study 005 failure shape, where verbose output outscored planted facts by
    accumulating incidental names and numbers over length.
    """
    plant = make_span(
        role=ROLE_ASSISTANT, word_count=7, named_entities=0, numeric_tokens=1
    )
    decoy = make_span(
        role=ROLE_ASSISTANT, word_count=55, named_entities=4, numeric_tokens=3
    )

    plant_base, _, plant_salience = calculate_span_salience(plant)
    decoy_base, _, decoy_salience = calculate_span_salience(decoy)

    assert decoy_base > plant_base, "fixture must reproduce the 005 failure shape"
    assert plant_salience > decoy_salience


def test_dense_assistant_span_can_still_outrank_sparse_user_span():
    """Source weight is a tiebreaker, not a domination weight."""
    sparse_user = make_span(
        role=ROLE_USER, word_count=40, named_entities=1, numeric_tokens=0
    )
    dense_assistant = make_span(
        role=ROLE_ASSISTANT, word_count=8, named_entities=1, numeric_tokens=1
    )

    assert (
        calculate_span_salience(dense_assistant)[2]
        > calculate_span_salience(sparse_user)[2]
    )


def test_zero_word_span_does_not_divide_by_zero():
    span = make_span(word_count=0, named_entities=1, numeric_tokens=1)

    assert calculate_span_salience(span) == (3, 0.0, 0.0)


# --- S6-T-007: dedup, cap, floor, marker ---------------------------------


def test_near_duplicate_spans_collapse_keeping_higher_salience():
    engine = SpanDreamEngine(conn=None)
    strong = candidate_from(
        make_span(word_count=6, named_entities=1, numeric_tokens=1, start=0),
        embedding=[1.0, 0.0],
    )
    weak = candidate_from(
        make_span(word_count=30, named_entities=1, numeric_tokens=0, start=100),
        embedding=[0.999, 0.0447],
    )

    survivors = engine.deduplicate([strong, weak])

    assert len(survivors) == 1
    assert survivors[0] is strong
    assert weak.key in survivors[0].collapsed_span_keys


def test_distinct_spans_do_not_collapse():
    engine = SpanDreamEngine(conn=None)
    first = candidate_from(make_span(start=0), embedding=[1.0, 0.0])
    second = candidate_from(make_span(start=50), embedding=[0.0, 1.0])

    assert len(engine.deduplicate([first, second])) == 2


def test_cap_limits_selection():
    """Amendment 001 raised C from 3 to 50; the cap must still bind."""
    engine = SpanDreamEngine(conn=None, salience_floor=0.0)
    candidates = [
        candidate_from(
            make_span(
                word_count=6,
                named_entities=1 + index % 5,
                numeric_tokens=1,
                start=index * 100,
            )
        )
        for index in range(engine.PER_TOPIC_CAP + 12)
    ]

    assert len(engine.select(candidates)) == engine.PER_TOPIC_CAP


def test_floor_is_applied_per_span_not_only_to_the_top_span():
    """Amendment 001. At C=50 a top-span-only floor would admit sub-floor junk."""
    engine = SpanDreamEngine(conn=None, salience_floor=0.15)
    strong = candidate_from(
        make_span(word_count=6, named_entities=1, numeric_tokens=1, start=0)
    )
    weak = candidate_from(
        make_span(
            role=ROLE_ASSISTANT,
            word_count=60,
            named_entities=1,
            numeric_tokens=0,
            start=500,
        )
    )

    assert strong.salience >= 0.15
    assert weak.salience < 0.15

    selected = engine.select([strong, weak])

    assert strong in selected
    assert weak not in selected


def test_all_sub_floor_topic_selects_nothing():
    engine = SpanDreamEngine(conn=None, salience_floor=0.15)
    sparse = [
        candidate_from(
            make_span(
                role=ROLE_ASSISTANT,
                word_count=60,
                named_entities=1,
                numeric_tokens=0,
                start=index * 100,
            )
        )
        for index in range(3)
    ]

    assert all(c.salience < 0.15 for c in sparse)
    assert engine.select(sparse) == []


def test_clearing_topic_selects_records():
    engine = SpanDreamEngine(conn=None, salience_floor=0.15)
    clearing = candidate_from(
        make_span(word_count=7, named_entities=0, numeric_tokens=1)
    )

    assert clearing.salience >= 0.15
    assert engine.select([clearing]) == [clearing]


def test_ranking_is_deterministic_for_tied_salience():
    engine = SpanDreamEngine(conn=None)
    later = candidate_from(
        make_span(start=10, turn_number=9, episode_id="b"),
    )
    earlier = candidate_from(
        make_span(start=10, turn_number=4, episode_id="a"),
    )

    assert engine.select([later, earlier])[0] is earlier


# --- S6-T-008: write records + span-level extractive assertion -----------


@pytest.fixture
def store(tmp_path):
    conn = init_db(str(tmp_path / "study.db"))
    yield conn
    conn.close()


def seed_topic_and_episodes(conn, texts):
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    embedding = np.zeros(1024, dtype=np.float32).tobytes()
    conn.execute(
        "INSERT INTO topics (id, label, centroid, episode_count, created_at, "
        "last_updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        ("topic-1", "civil engineering", embedding, len(texts), now, now),
    )
    episode_ids = []
    for index, (user_message, assistant_message) in enumerate(texts, start=1):
        episode_id = f"episode-{index}"
        text = f"User: {user_message}\nAssistant: {assistant_message}"
        conn.execute(
            "INSERT INTO episodes (id, topic_id, user_message, "
            "assistant_message, embedding, turn_number, created_at, role, "
            "text, dreamed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (
                episode_id,
                "topic-1",
                user_message,
                assistant_message,
                embedding,
                index,
                now,
                "conversation",
                text,
            ),
        )
        episode_ids.append(episode_id)
    conn.commit()
    return episode_ids


def counting_embed(text):
    """Deterministic non-degenerate embedding, independent of the real model."""
    vector = np.zeros(8, dtype=np.float32)
    for index, char in enumerate(text[:64]):
        vector[index % 8] += (ord(char) % 17) / 17.0
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def test_records_store_span_provenance_and_pass_offset_assertion(store):
    seed_topic_and_episodes(
        store,
        [
            (
                "The total main span is 847 meters. The lead structural "
                "engineer assigned to the project is Dr. Anara Bekova.",
                "Acknowledged.",
            ),
            (
                "The steel specification is grade S460ML for all primary members.",
                "1. Yield strength is 460 MPa. 2. Risk: Low.",
            ),
            ("What is the axle load rating?", "It is 92.4 metric tons."),
        ],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)

    summary = engine._process_topic("topic-1", 31, "transition")

    assert summary is not None
    assert summary.records_written >= 1
    assert summary.inference_calls == 0
    assert summary.marker_written is False

    records = get_distilled_records(store)
    content = [r for r in records if r["status"] == CONTENT_STATUS]
    assert content

    for record in content:
        assert_span_record_faithful(store, record["id"])
        source = store.execute(
            "SELECT text FROM episodes WHERE id = ?",
            (record["source_episode_id"],),
        ).fetchone()[0]
        row = store.execute(
            "SELECT span_start, span_end, role, density, salience_score, "
            "segmenter FROM distilled_ltm WHERE id = ?",
            (record["id"],),
        ).fetchone()
        span_start, span_end, role, density, salience_score, segmenter = row
        assert source[span_start:span_end] == record["text"]
        assert role in {ROLE_USER, ROLE_ASSISTANT}
        assert density > 0
        assert salience_score > 0
        assert segmenter


def test_source_episodes_are_marked_dreamed(store):
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)
    engine._process_topic("topic-1", 31, "transition")

    undreamed = store.execute(
        "SELECT COUNT(*) FROM episodes WHERE dreamed = 0"
    ).fetchone()[0]
    assert undreamed == 0


def test_offset_assertion_trips_on_mangled_record(store):
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)
    summary = engine._process_topic("topic-1", 31, "transition")
    distilled_id = summary.distilled_ids[0]

    assert_span_record_faithful(store, distilled_id)

    store.execute(
        "UPDATE distilled_ltm SET text = ? WHERE id = ?",
        ("The total main span is 999 meters.", distilled_id),
    )
    store.commit()

    with pytest.raises(AssertionError, match="recorded character offsets"):
        assert_span_record_faithful(store, distilled_id)


def test_offset_assertion_trips_when_offsets_are_shifted(store):
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)
    summary = engine._process_topic("topic-1", 31, "transition")
    distilled_id = summary.distilled_ids[0]

    store.execute(
        "UPDATE distilled_ltm SET span_start = span_start + 1 WHERE id = ?",
        (distilled_id,),
    )
    store.commit()

    with pytest.raises(AssertionError, match="recorded character offsets"):
        assert_span_record_faithful(store, distilled_id)


def test_dream_pass_trips_when_inference_is_invoked(store):
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    calls = iter([0, 1])
    engine = SpanDreamEngine(
        store,
        inference_call_count=lambda: next(calls),
        embed_fn=counting_embed,
    )

    with pytest.raises(AssertionError, match="invoked the inference model"):
        engine._process_topic("topic-1", 31, "transition")


def test_sub_floor_topic_writes_marker_not_a_forced_record(store):
    seed_topic_and_episodes(
        store,
        [
            (
                "I think that is broadly reasonable and we should probably "
                "continue in the same general direction as before for now.",
                "That seems sensible to me as well given everything so far.",
            ),
            (
                "Let us keep going with the current approach and revisit it "
                "later once we have more information available to us.",
                "Understood, and I will proceed exactly along those lines.",
            ),
            (
                "It would be good to review the overall situation again at "
                "some later point when circumstances allow for that review.",
                "Agreed, and I will wait for your guidance before acting.",
            ),
        ],
    )
    engine = SpanDreamEngine(
        store, embed_fn=counting_embed, salience_floor=10.0
    )

    summary = engine._process_topic("topic-1", 31, "transition")

    assert summary.records_written == 0
    assert summary.marker_written is True
    statuses = [r["status"] for r in get_distilled_records(store)]
    assert statuses == [NO_SALIENT_FACT_STATUS]


def test_eligible_but_sub_floor_topic_writes_marker_referencing_best_span(store):
    """Distinct from the no-eligible-spans path: here candidates exist but none clear F."""
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    engine = SpanDreamEngine(
        store, embed_fn=counting_embed, salience_floor=99.0
    )

    summary = engine._process_topic("topic-1", 31, "transition")

    assert summary.spans_eligible > 0, "this path needs real candidates"
    assert summary.records_written == 0
    assert summary.marker_written is True
    records = get_distilled_records(store)
    assert [r["status"] for r in records] == [NO_SALIENT_FACT_STATUS]
    assert records[0]["text"] is None


def test_span_inventory_logs_eligible_and_rejected_spans(store):
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters. Sure.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)
    engine._process_topic("topic-1", 31, "transition")

    rows = store.execute(
        "SELECT eligible, rejection_reason, selected FROM span_inventory"
    ).fetchall()

    assert rows
    assert any(eligible == 0 and reason for eligible, reason, _ in rows)
    assert any(selected == 1 for _, _, selected in rows)


def test_dream_event_records_segmenter_and_span_counts(store):
    seed_topic_and_episodes(
        store,
        [
            ("The total main span is 847 meters.", "Acknowledged."),
            ("The steel grade is S460ML for primary members.", "Noted."),
            ("The axle rating is 92.4 metric tons.", "Understood."),
        ],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)
    engine._process_topic("topic-1", 31, "transition")

    row = store.execute(
        "SELECT segmenter, spans_evaluated, spans_eligible, salience_floor, "
        "extractor, inference_calls FROM dream_events"
    ).fetchone()
    segmenter, spans_evaluated, spans_eligible, floor, extractor, calls = row

    assert segmenter
    assert extractor
    assert spans_evaluated >= spans_eligible >= 1
    assert floor == pytest.approx(SpanDreamEngine.SALIENCE_FLOOR)
    assert calls == 0


def test_topic_below_minimum_episode_count_is_skipped(store):
    seed_topic_and_episodes(
        store,
        [("The total main span is 847 meters.", "Acknowledged.")],
    )
    engine = SpanDreamEngine(store, embed_fn=counting_embed)

    assert engine._process_topic("topic-1", 31, "transition") is None


def test_real_episode_spans_score_end_to_end():
    """Segmentation and scoring compose on the real turn-3 text."""
    user_message = (
        "We are beginning work on a major infrastructure project called "
        "Halcyon Crossing — a long-span cable-stayed bridge. The total main "
        "span is 847 meters. The lead structural engineer assigned to the "
        "project is Dr. Anara Bekova. Please acknowledge these project "
        "parameters."
    )
    episode = {
        "id": "episode-1",
        "turn_number": 3,
        "user_message": user_message,
        "assistant_message": "Acknowledged.",
        "text": f"User: {user_message}\nAssistant: Acknowledged.",
    }
    spans = [s for s in segment_episode(episode) if s.eligible]
    scored = sorted(
        ((calculate_span_salience(s)[2], s) for s in spans),
        key=lambda pair: -pair[0],
    )

    assert scored
    top_text = scored[0][1].text
    assert "847" in top_text or "Anara Bekova" in top_text
