"""S6_004 — the adversarial fixture must discriminate between the two policies.

S6-T-010 requires both directions. Under the Study 006 policy the planted fact is
selected, the decoys do not crowd it out, and the acknowledgment is excluded.
Under the Study 005 policy the plant is *not* selected. A fixture that passes
under both policies does not test the change and must be rewritten.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from src.db.schema import init_db
from src.memory.distilled_ltm_store import CONTENT_STATUS, get_distilled_records
from src.memory.dream_engine import DreamEngine, calculate_salience
from src.memory.span_dream_engine import SpanDreamEngine, calculate_span_salience
from src.memory.span_segmenter import ROLE_USER, segment_episode

FIXTURE_PATH = Path(__file__).parent / "adversarial_selection_fixture.json"


@pytest.fixture(scope="module")
def fixture():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def episodes(fixture):
    built = []
    for entry in fixture["episodes"]:
        episode = dict(entry)
        episode["text"] = (
            f"User: {episode['user_message']}\n"
            f"Assistant: {episode['assistant_message']}"
        )
        built.append(episode)
    return built


@pytest.fixture(scope="module")
def plant_text(fixture):
    return fixture["episodes"][0]["plant_span"]


@pytest.fixture(scope="module")
def acknowledgment_text(fixture):
    return next(
        entry["acknowledgment_span"]
        for entry in fixture["episodes"]
        if entry["kind"] == "acknowledgment"
    )


def scored_spans(episodes):
    rows = []
    for episode in episodes:
        for span in segment_episode(episode):
            base, density, salience = calculate_span_salience(span)
            rows.append(
                {
                    "episode": episode,
                    "span": span,
                    "base": base,
                    "density": density,
                    "salience": salience,
                }
            )
    return rows


def seed(conn, episodes):
    """Seed the fixture with mutually orthogonal embeddings so nothing collapses."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO topics (id, label, centroid, episode_count, created_at, "
        "last_updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            "topic-adversarial",
            "structural analysis",
            np.zeros(1024, dtype=np.float32).tobytes(),
            len(episodes),
            now,
            now,
        ),
    )
    for index, episode in enumerate(episodes):
        vector = np.zeros(1024, dtype=np.float32)
        vector[index] = 1.0
        conn.execute(
            "INSERT INTO episodes (id, topic_id, user_message, "
            "assistant_message, embedding, turn_number, created_at, role, "
            "text, dreamed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
            (
                episode["id"],
                "topic-adversarial",
                episode["user_message"],
                episode["assistant_message"],
                vector.tobytes(),
                episode["turn_number"],
                now,
                "conversation",
                episode["text"],
            ),
        )
    conn.commit()


def orthogonal_embed_factory():
    """Give each distinct span its own axis so dedup never fires in this fixture."""
    seen: dict[str, int] = {}

    def embed(text: str) -> np.ndarray:
        index = seen.setdefault(text, len(seen))
        vector = np.zeros(1024, dtype=np.float32)
        vector[index % 1024] = 1.0
        return vector

    return embed


# --- fixture integrity: the relationships must not silently drift --------


def test_decoy_spans_have_higher_absolute_counts_than_the_plant(
    episodes, plant_text
):
    rows = scored_spans(episodes)
    plant = next(r for r in rows if r["span"].text == plant_text)
    decoys = [
        r
        for r in rows
        if r["episode"]["kind"] == "decoy" and r["span"].eligible
    ]
    higher = [r for r in decoys if r["base"] > plant["base"]]

    assert len(higher) >= 3, (
        "the fixture must contain at least three decoy spans whose absolute "
        "entity+numeric count exceeds the plant's, or it does not reproduce "
        "the Study 005 failure shape"
    )


def test_plant_span_has_the_highest_density(episodes, plant_text):
    """The plant must win on density alone, before source weighting."""
    rows = scored_spans(episodes)
    plant = next(r for r in rows if r["span"].text == plant_text)
    others = [
        r
        for r in rows
        if r["span"].eligible and r["span"].text != plant_text
    ]

    assert others
    assert all(r["density"] < plant["density"] for r in others), (
        "if a decoy matched the plant's density the fixture would only be "
        "testing the 1.5x source weight, not the density correction"
    )


def test_plant_outranks_every_decoy_on_density_before_source_weight(
    episodes, plant_text
):
    rows = scored_spans(episodes)
    plant = next(r for r in rows if r["span"].text == plant_text)
    decoys = [
        r
        for r in rows
        if r["episode"]["kind"] == "decoy" and r["span"].eligible
    ]
    best_decoy = max(decoys, key=lambda r: r["density"])

    assert plant["density"] > best_decoy["density"]
    assert plant["span"].role == ROLE_USER


def test_acknowledgment_span_is_eligible_but_sub_floor(
    episodes, acknowledgment_text
):
    rows = scored_spans(episodes)
    ack = next(r for r in rows if r["span"].text == acknowledgment_text)

    assert ack["span"].eligible, (
        "the acknowledgment should reach scoring so the floor is what "
        "excludes it, not the eligibility filter"
    )
    assert ack["salience"] < SpanDreamEngine.SALIENCE_FLOOR


def test_plant_episode_is_outranked_under_absolute_counts(episodes):
    """The 005-side precondition: the plant's whole turn ranks below the cap."""
    ranked = sorted(
        ((calculate_salience(e["text"])[0], e) for e in episodes),
        key=lambda pair: (-pair[0], pair[1]["turn_number"]),
    )
    plant_rank = next(
        rank
        for rank, (_, episode) in enumerate(ranked, start=1)
        if episode["kind"] == "plant"
    )

    assert plant_rank > DreamEngine.PER_TOPIC_CAP


# --- S6-T-010: run the fixture both ways ---------------------------------


def test_study_006_policy_selects_the_plant(
    tmp_path, episodes, plant_text, acknowledgment_text
):
    conn = init_db(str(tmp_path / "v6.db"))
    try:
        seed(conn, episodes)
        engine = SpanDreamEngine(conn, embed_fn=orthogonal_embed_factory())
        summary = engine._process_topic("topic-adversarial", 31, "transition")

        assert summary is not None
        assert summary.inference_calls == 0
        assert summary.marker_written is False

        selected = [candidate.span.text for candidate in summary.selected]
        assert plant_text in selected, (
            "Study 006 policy must select the planted fact"
        )
        assert acknowledgment_text not in selected, (
            "the sub-floor acknowledgment must be excluded"
        )
        assert len(selected) <= SpanDreamEngine.PER_TOPIC_CAP

        stored = [
            record["text"]
            for record in get_distilled_records(conn)
            if record["status"] == CONTENT_STATUS
        ]
        assert plant_text in stored
    finally:
        conn.close()


def test_plant_is_ranked_first_and_not_crowded_out(tmp_path, episodes, plant_text):
    conn = init_db(str(tmp_path / "v6_rank.db"))
    try:
        seed(conn, episodes)
        engine = SpanDreamEngine(conn, embed_fn=orthogonal_embed_factory())
        summary = engine._process_topic("topic-adversarial", 31, "transition")

        assert summary.selected[0].span.text == plant_text, (
            "the plant should not merely survive the cap - it should lead"
        )
    finally:
        conn.close()


def test_study_005_policy_does_not_select_the_plant(
    tmp_path, episodes, plant_text
):
    conn = init_db(str(tmp_path / "v5.db"))
    try:
        seed(conn, episodes)
        engine = DreamEngine(conn)
        summary = engine._process_topic("topic-adversarial", 31, "transition")

        assert summary is not None
        assert summary.records_written == DreamEngine.PER_TOPIC_CAP

        selected_ids = {c.episode["id"] for c in summary.selected}
        assert "episode-plant" not in selected_ids, (
            "Study 005 policy must bury the plant, otherwise the fixture "
            "does not discriminate between the policies"
        )

        stored = [
            record["text"]
            for record in get_distilled_records(conn)
            if record["status"] == CONTENT_STATUS
        ]
        assert not any(plant_text in text for text in stored), (
            "the planted fact must not reach the distilled store under the "
            "Study 005 policy"
        )
    finally:
        conn.close()


def test_the_two_policies_disagree_on_this_fixture(tmp_path, episodes, plant_text):
    """The single assertion that makes the fixture meaningful."""
    v6_conn = init_db(str(tmp_path / "both_v6.db"))
    v5_conn = init_db(str(tmp_path / "both_v5.db"))
    try:
        seed(v6_conn, episodes)
        seed(v5_conn, episodes)

        v6 = SpanDreamEngine(v6_conn, embed_fn=orthogonal_embed_factory())
        v6_summary = v6._process_topic("topic-adversarial", 31, "transition")
        v6_selected = plant_text in [c.span.text for c in v6_summary.selected]

        v5 = DreamEngine(v5_conn)
        v5_summary = v5._process_topic("topic-adversarial", 31, "transition")
        v5_selected = any(
            plant_text in c.episode["text"] for c in v5_summary.selected
        )

        assert v6_selected is True
        assert v5_selected is False
    finally:
        v6_conn.close()
        v5_conn.close()
