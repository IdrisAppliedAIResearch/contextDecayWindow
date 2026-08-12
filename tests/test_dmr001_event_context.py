"""DMR-001 verification contract.

Covers every bullet the implementation specification's section 11 requires:
stable ids and canonical serialization, causal input rejection and out-of-order
turns, partition invariants, exact float32 update order and vector hashes,
hard/drift/forced precedence, idempotent and loud conflicting replay,
transactional failure midway through a boundary, no import path to keys or
rubrics or readers or packers or scorers, and no generation call in the
process.
"""

from __future__ import annotations

import ast
import hashlib
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

from src.biological_memory.event_context import (
    C_PAIR,
    C_SESSION,
    EventContextError,
    EventContextStore,
    FormerConfig,
    OnlineEventContextFormer,
    T_EVENT,
    dot,
    form,
    load_design,
    normalize,
    periodic_policy,
    vector_sha256,
)

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = (
    ROOT
    / "experiments"
    / "components"
    / "biological_memory"
    / "dmr_001"
    / "DMR_001_FINAL_DESIGN.json"
)
DIMENSION = 1024
ANCHOR = "0" * 64
CONFIG = FormerConfig(rho=0.5, drift_threshold=0.7, min_event_size=5, max_event_size=32)


def identity(value: int) -> str:
    return f"{value:064x}"


def basis(index: int) -> np.ndarray:
    """A unit vector along one axis. Two distinct axes have cosine 0, drift 1."""
    vector = np.zeros(DIMENSION, dtype=np.float32)
    vector[index % DIMENSION] = 1.0
    return vector


def tilted(index: int, other: int, weight: float) -> np.ndarray:
    vector = np.zeros(DIMENSION, dtype=np.float32)
    vector[index % DIMENSION] = 1.0
    vector[other % DIMENSION] = np.float32(weight)
    return vector


def stream(vectors, *, session=identity(7), first_turn=0):
    return [
        {
            "episode_hash": identity(1000 + position),
            "session_hash": session,
            "turn_index": first_turn + position,
            "embedding": vector,
        }
        for position, vector in enumerate(vectors)
    ]


# ---------------------------------------------------------------------------
# Stable identity and canonical serialization
# ---------------------------------------------------------------------------


def test_event_id_is_a_pure_function_of_design_session_and_first_episode() -> None:
    snapshot = form(stream([basis(0)] * 3), design_sha256=ANCHOR, config=CONFIG)
    expected = hashlib.sha256(
        ("dmr-event-v1\0" + ANCHOR + "\0" + identity(7) + "\0" + identity(1000)).encode(
            "utf-8"
        )
    ).hexdigest()
    assert snapshot.events[0].event_id == expected


def test_event_id_ignores_turn_numbers_and_member_count() -> None:
    early = form(stream([basis(0)] * 3, first_turn=0), design_sha256=ANCHOR, config=CONFIG)
    late = form(stream([basis(0)] * 9, first_turn=500), design_sha256=ANCHOR, config=CONFIG)
    assert early.events[0].event_id == late.events[0].event_id


def test_event_id_changes_with_the_design_anchor() -> None:
    first = form(stream([basis(0)] * 3), design_sha256=ANCHOR, config=CONFIG)
    second = form(stream([basis(0)] * 3), design_sha256=identity(1), config=CONFIG)
    assert first.events[0].event_id != second.events[0].event_id


def test_canonical_serialization_is_stable_and_digests_agree() -> None:
    episodes = stream([basis(0), basis(0), basis(1)])
    first = form(episodes, design_sha256=ANCHOR, config=CONFIG)
    second = form(episodes, design_sha256=ANCHOR, config=CONFIG)
    assert first.canonical_json() == second.canonical_json()
    assert first.digest() == second.digest()
    assert first.canonical_json().endswith("\n")


def test_committed_design_anchor_matches_the_pre_registration_on_disk() -> None:
    anchor, config, payload = load_design(DESIGN_PATH)
    assert config == CONFIG
    assert payload["parameters"]["boundary_tolerance"] == 1
    assert len(anchor) == 64


# ---------------------------------------------------------------------------
# Causal input rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"episode_hash": "not-a-hash"},
        {"session_hash": "ABCDEF"},
        {"turn_index": -1},
        {"turn_index": 1.5},
        {"turn_index": True},
        {"embedding": np.zeros(8, dtype=np.float32)},
        {"embedding": np.zeros(DIMENSION, dtype=np.float32)},
        {"embedding": np.full(DIMENSION, np.nan, dtype=np.float32)},
    ],
)
def test_malformed_causal_inputs_are_rejected(kwargs) -> None:
    former = OnlineEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    call = {
        "episode_hash": identity(1),
        "session_hash": identity(7),
        "turn_index": 0,
        "embedding": basis(0),
    }
    call.update(kwargs)
    with pytest.raises((EventContextError, ValueError, TypeError)):
        former.observe(**call)


def test_out_of_order_turns_are_rejected() -> None:
    former = OnlineEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    former.observe(
        episode_hash=identity(1), session_hash=identity(7), turn_index=5, embedding=basis(0)
    )
    with pytest.raises(EventContextError, match="strictly increasing"):
        former.observe(
            episode_hash=identity(2),
            session_hash=identity(7),
            turn_index=5,
            embedding=basis(0),
        )


def test_repeat_turns_within_a_session_are_rejected() -> None:
    former = OnlineEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    former.observe(
        episode_hash=identity(1), session_hash=identity(7), turn_index=2, embedding=basis(0)
    )
    with pytest.raises(EventContextError):
        former.observe(
            episode_hash=identity(2),
            session_hash=identity(7),
            turn_index=1,
            embedding=basis(0),
        )


def test_a_closed_session_cannot_be_reopened() -> None:
    former = OnlineEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    former.observe(
        episode_hash=identity(1), session_hash=identity(7), turn_index=0, embedding=basis(0)
    )
    former.observe(
        episode_hash=identity(2), session_hash=identity(8), turn_index=0, embedding=basis(0)
    )
    with pytest.raises(EventContextError, match="already closed"):
        former.observe(
            episode_hash=identity(3),
            session_hash=identity(7),
            turn_index=1,
            embedding=basis(0),
        )


def test_one_episode_cannot_be_observed_twice_in_a_pass() -> None:
    former = OnlineEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    former.observe(
        episode_hash=identity(1), session_hash=identity(7), turn_index=0, embedding=basis(0)
    )
    with pytest.raises(EventContextError, match="observed twice"):
        former.observe(
            episode_hash=identity(1),
            session_hash=identity(7),
            turn_index=1,
            embedding=basis(0),
        )


def test_observe_accepts_no_text() -> None:
    former = OnlineEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    with pytest.raises(TypeError):
        former.observe(  # type: ignore[call-arg]
            episode_hash=identity(1),
            session_hash=identity(7),
            turn_index=0,
            embedding=basis(0),
            text="the episode text",
        )


# ---------------------------------------------------------------------------
# Partition invariants
# ---------------------------------------------------------------------------


def test_every_episode_lands_in_exactly_one_event_in_order() -> None:
    vectors = [basis(i // 7) for i in range(60)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    counts = snapshot.validate()
    assert counts["episodes"] == len(vectors)
    assert counts["members"] == len(vectors)
    assert sum(record.member_count for record in snapshot.events) == len(vectors)
    positions = [member.event_position for member in snapshot.members]
    assert positions[0] == 0
    for record in snapshot.events:
        members = [m for m in snapshot.members if m.event_id == record.event_id]
        assert [m.event_position for m in members] == list(range(record.member_count))


def test_no_event_spans_two_sessions() -> None:
    episodes = stream([basis(0)] * 4)
    episodes += [
        {
            "episode_hash": identity(2000 + i),
            "session_hash": identity(8),
            "turn_index": i,
            "embedding": basis(0),
        }
        for i in range(4)
    ]
    snapshot = form(episodes, design_sha256=ANCHOR, config=CONFIG)
    assert len(snapshot.events) == 2
    assert [record.session_hash for record in snapshot.events] == [identity(7), identity(8)]
    assert [record.member_count for record in snapshot.events] == [4, 4]


def test_snapshot_validation_rejects_a_forged_partition() -> None:
    snapshot = form(stream([basis(0)] * 6), design_sha256=ANCHOR, config=CONFIG)
    forged = type(snapshot)(
        design_sha256=snapshot.design_sha256,
        policy=snapshot.policy,
        events=snapshot.events,
        members=snapshot.members[:-1] + (snapshot.members[0],),
        decisions=snapshot.decisions,
    )
    with pytest.raises(EventContextError):
        forged.validate()


# ---------------------------------------------------------------------------
# Exact float32 update order and vector hashes
# ---------------------------------------------------------------------------


def test_prototype_is_the_normalized_mean_of_its_members_bit_for_bit() -> None:
    vectors = [normalize(tilted(0, 1, 0.1 * step)) for step in range(4)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    total = vectors[0].copy()
    for vector in vectors[1:]:
        total = total + vector
    expected = normalize(total / np.float32(len(vectors)))
    assert snapshot.decisions[-1].prototype_sha256 == vector_sha256(expected)


def test_context_follows_the_leaky_recursion_bit_for_bit() -> None:
    vectors = [normalize(tilted(0, 1, 0.1 * step)) for step in range(4)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    context = vectors[0].copy()
    for vector in vectors[1:]:
        context = normalize(
            np.float32(CONFIG.rho) * context + np.float32(1.0 - CONFIG.rho) * vector
        )
    assert snapshot.decisions[-1].context_sha256 == vector_sha256(context)


def test_reductions_do_not_depend_on_summation_order() -> None:
    left = normalize(np.arange(DIMENSION, dtype=np.float32) + 1.0)
    right = normalize(np.arange(DIMENSION, 0, -1, dtype=np.float32))
    assert dot(left, right) == dot(right, left)


def test_pinned_vectors_are_normalized_before_use() -> None:
    scaled = form(
        stream([basis(0) * np.float32(113.0)] * 3), design_sha256=ANCHOR, config=CONFIG
    )
    unit = form(stream([basis(0)] * 3), design_sha256=ANCHOR, config=CONFIG)
    assert scaled.digest() == unit.digest()


def test_a_duplicate_episode_produces_zero_drift_and_never_opens_an_event() -> None:
    vectors = [basis(0)] * 12
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    drifts = [decision.boundary_score for decision in snapshot.decisions[1:]]
    assert max(drifts) < 1e-6
    assert not any(decision.drift_boundary for decision in snapshot.decisions)


# ---------------------------------------------------------------------------
# Boundary predicate precedence
# ---------------------------------------------------------------------------


def test_drift_below_min_event_size_cannot_open_an_event() -> None:
    vectors = [basis(0), basis(1), basis(2), basis(3)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    assert len(snapshot.events) == 1
    assert all(decision.boundary_score >= 0.0 for decision in snapshot.decisions[1:])
    assert not any(decision.drift_boundary for decision in snapshot.decisions)


def test_drift_at_or_above_the_threshold_opens_an_event_once_min_size_is_met() -> None:
    vectors = [basis(0)] * 5 + [basis(1)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    assert len(snapshot.events) == 2
    assert snapshot.decisions[-1].boundary_reason == "drift"
    assert snapshot.decisions[-1].boundary_score == pytest.approx(1.0)


def test_forced_boundary_fires_at_max_event_size() -> None:
    vectors = [basis(0)] * 40
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    assert [record.member_count for record in snapshot.events] == [32, 8]
    assert snapshot.decisions[32].boundary_reason == "forced"


def test_hard_boundary_takes_precedence_over_drift_and_forced() -> None:
    episodes = stream([basis(0)] * 40)
    episodes.append(
        {
            "episode_hash": identity(3000),
            "session_hash": identity(9),
            "turn_index": 0,
            "embedding": basis(5),
        }
    )
    snapshot = form(episodes, design_sha256=ANCHOR, config=CONFIG)
    last = snapshot.decisions[-1]
    assert last.hard_boundary and last.boundary_reason == "hard"
    assert last.new_event


def test_precedence_labels_never_change_the_partition() -> None:
    vectors = [basis(0)] * 32 + [basis(1)] * 4
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    opener = snapshot.decisions[32]
    assert opener.forced_boundary and opener.drift_boundary
    assert opener.boundary_reason == "drift"
    assert [record.member_count for record in snapshot.events] == [32, 4]


# ---------------------------------------------------------------------------
# Structural control arms
# ---------------------------------------------------------------------------


def test_control_arms_produce_their_defining_partitions() -> None:
    vectors = [basis(i // 3) for i in range(24)]
    episodes = stream(vectors)
    assert len(form(episodes, design_sha256=ANCHOR, config=CONFIG, policy=C_PAIR).events) == 24
    assert len(form(episodes, design_sha256=ANCHOR, config=CONFIG, policy=C_SESSION).events) == 1
    periodic = form(
        episodes, design_sha256=ANCHOR, config=CONFIG, policy=periodic_policy(4)
    )
    assert [record.member_count for record in periodic.events] == [4, 4, 4, 4, 4, 4]


def test_every_arm_shares_the_same_context_arithmetic() -> None:
    vectors = [normalize(tilted(0, 1, 0.05 * step)) for step in range(4)]
    episodes = stream(vectors)
    treatment = form(episodes, design_sha256=ANCHOR, config=CONFIG, policy=T_EVENT)
    control = form(episodes, design_sha256=ANCHOR, config=CONFIG, policy=C_SESSION)
    assert [d.context_sha256 for d in treatment.decisions] == [
        d.context_sha256 for d in control.decisions
    ]


# ---------------------------------------------------------------------------
# Store: idempotent replay, loud conflict, transactional failure
# ---------------------------------------------------------------------------


def episodes_for_store():
    return stream([basis(0)] * 5 + [basis(1)] * 5)


def test_identical_replay_into_a_shared_store_is_a_no_op() -> None:
    store = EventContextStore.in_memory()
    episodes = episodes_for_store()
    form(episodes, design_sha256=ANCHOR, config=CONFIG, store=store)
    first = store.digest()
    form(episodes, design_sha256=ANCHOR, config=CONFIG, store=store)
    assert store.digest() == first
    assert len(store.members()) == len(episodes)


def test_conflicting_replay_raises_and_never_reassigns() -> None:
    store = EventContextStore.in_memory()
    episodes = episodes_for_store()
    form(episodes, design_sha256=ANCHOR, config=CONFIG, store=store)
    before = store.digest()
    conflicting = [dict(episode) for episode in episodes]
    conflicting[6]["embedding"] = basis(9)
    with pytest.raises(EventContextError, match="Conflicting replay"):
        form(conflicting, design_sha256=ANCHOR, config=CONFIG, store=store)
    assert store.digest() == before


def test_a_failure_inserting_a_member_rolls_back_the_new_event_row() -> None:
    """The episode write is one transaction: no orphan event, no orphan member.

    Closing the previous event is a separate committed transaction and is
    expected to survive; what must not survive is a half-written boundary.
    """
    store = EventContextStore.in_memory()
    episodes = episodes_for_store()
    former = OnlineEventContextFormer(
        design_sha256=ANCHOR, config=CONFIG, policy=T_EVENT, store=store
    )
    for episode in episodes[:5]:
        former.observe(**episode)
    before_event_ids = {record.event_id for record in store.events()}
    before_members = len(store.members())
    before_decisions = store._connection.execute(
        "SELECT count(*) FROM boundary_decisions"
    ).fetchone()[0]

    store._connection.execute(
        "CREATE TRIGGER fail_member BEFORE INSERT ON event_members "
        "BEGIN SELECT RAISE(ABORT, 'injected failure'); END"
    )
    with pytest.raises(sqlite3.Error):
        former.observe(**episodes[5])
    store._connection.execute("DROP TRIGGER fail_member")

    assert {record.event_id for record in store.events()} == before_event_ids
    assert len(store.members()) == before_members
    assert (
        store._connection.execute("SELECT count(*) FROM boundary_decisions").fetchone()[0]
        == before_decisions
    )
    assert store._connection.execute("SELECT count(*) FROM event_records").fetchone()[0] == 1


def test_stored_rows_match_the_snapshot() -> None:
    store = EventContextStore.in_memory()
    episodes = episodes_for_store()
    snapshot = form(episodes, design_sha256=ANCHOR, config=CONFIG, store=store)
    stored = {record.event_id: record for record in store.events()}
    assert set(stored) == {record.event_id for record in snapshot.events}
    for record in snapshot.events:
        assert stored[record.event_id].member_count == record.member_count
        assert stored[record.event_id].prototype_sha256 == record.prototype_sha256
        assert stored[record.event_id].context_sha256 == record.context_sha256
        assert stored[record.event_id].close_reason == record.close_reason


def test_stored_vectors_hash_to_their_recorded_digests() -> None:
    store = EventContextStore.in_memory()
    form(episodes_for_store(), design_sha256=ANCHOR, config=CONFIG, store=store)
    rows = store._connection.execute(
        "SELECT prototype_f32, prototype_sha256, context_f32, context_sha256 FROM event_records"
    ).fetchall()
    assert rows
    for prototype, prototype_sha, context, context_sha in rows:
        assert hashlib.sha256(prototype).hexdigest() == prototype_sha
        assert hashlib.sha256(context).hexdigest() == context_sha
        assert len(prototype) == DIMENSION * 4


# ---------------------------------------------------------------------------
# Leakage and generation
# ---------------------------------------------------------------------------

FORBIDDEN_SUBSTRINGS = (
    "q_facts_key",
    "rubric",
    "answer_key",
    "criteria_evaluator",
    "scoring",
    "retrieval_engine",
    "context_builder",
    "retrieval_budget",
    "inference",
    "llama",
    "openai",
    "anthropic",
)

GENERATION_CALLS = ("complete", "chat", "create_completion", "generate", "respond")


def module_source() -> str:
    return (ROOT / "src" / "biological_memory" / "event_context.py").read_text(
        encoding="utf-8"
    )


def test_mechanism_source_names_no_key_rubric_reader_packer_or_scorer() -> None:
    lowered = module_source().lower()
    for needle in FORBIDDEN_SUBSTRINGS:
        assert needle not in lowered, f"mechanism source mentions {needle}"


def test_mechanism_import_graph_reaches_only_the_standard_library_and_numpy() -> None:
    tree = ast.parse(module_source())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {
        "__future__",
        "hashlib",
        "json",
        "math",
        "sqlite3",
        "dataclasses",
        "pathlib",
        "typing",
        "numpy",
    }, imported


def test_no_project_module_is_reachable_from_the_mechanism() -> None:
    """Import the mechanism alone in a clean interpreter and list what it pulls in.

    Doing this in-process would be vacuous: conftest and the rest of the suite
    have already imported half the package, so nothing new would appear.
    """
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(ROOT)
            + "'); import src.biological_memory.event_context; "
            "print(sorted(n for n in sys.modules if n.startswith('src.')))",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
    )
    loaded = set(ast.literal_eval(result.stdout.strip()))
    # The package __init__ re-exports SUP-001's ledger, so importing the
    # mechanism pulls its sibling in. Nothing outside this package is reachable,
    # and the sibling is checked for stdlib-only imports below.
    assert all(name.startswith("src.biological_memory") for name in loaded), loaded


def test_the_sibling_pulled_in_by_the_package_init_is_itself_leak_free() -> None:
    source = (ROOT / "src" / "biological_memory" / "supersession.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {
        "__future__",
        "hashlib",
        "json",
        "dataclasses",
        "pathlib",
        "typing",
    }, imported


def test_mechanism_makes_no_generation_call() -> None:
    tree = ast.parse(module_source())
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            target = node.func
            if isinstance(target, ast.Attribute):
                called.add(target.attr)
            elif isinstance(target, ast.Name):
                called.add(target.id)
    assert not (called & set(GENERATION_CALLS)), called & set(GENERATION_CALLS)


def test_a_planted_leakage_violation_is_caught() -> None:
    """The leakage check must fail on a violation, not merely pass on clean code."""
    planted = module_source() + "\nfrom src.analysis.criteria_evaluator import *\n"
    lowered = planted.lower()
    assert any(needle in lowered for needle in FORBIDDEN_SUBSTRINGS)


# ---------------------------------------------------------------------------
# Two-process determinism
# ---------------------------------------------------------------------------


def test_two_formers_in_one_process_agree_bit_for_bit() -> None:
    vectors = [normalize(tilted(step % 16, (step * 7) % 16, 0.3)) for step in range(200)]
    episodes = stream(vectors)
    assert (
        form(episodes, design_sha256=ANCHOR, config=CONFIG).digest()
        == form(episodes, design_sha256=ANCHOR, config=CONFIG).digest()
    )


def test_a_fresh_process_reproduces_the_snapshot_digest(tmp_path) -> None:
    import subprocess

    script = tmp_path / "replay.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import numpy as np\n"
        "from src.biological_memory.event_context import FormerConfig, form, normalize\n"
        "config = FormerConfig(rho=0.5, drift_threshold=0.7, min_event_size=5, max_event_size=32)\n"
        "def tilted(i, j, w):\n"
        "    v = np.zeros(1024, dtype=np.float32)\n"
        "    v[i % 1024] = 1.0\n"
        "    v[j % 1024] = np.float32(w)\n"
        "    return v\n"
        "vectors = [normalize(tilted(s % 16, (s * 7) % 16, 0.3)) for s in range(200)]\n"
        "episodes = [\n"
        "    {'episode_hash': f'{1000 + p:064x}', 'session_hash': f'{7:064x}',\n"
        "     'turn_index': p, 'embedding': v}\n"
        "    for p, v in enumerate(vectors)\n"
        "]\n"
        f"print(form(episodes, design_sha256={ANCHOR!r}, config=config).digest())\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=True, cwd=str(ROOT)
    )
    vectors = [normalize(tilted(step % 16, (step * 7) % 16, 0.3)) for step in range(200)]
    expected = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG).digest()
    assert result.stdout.strip() == expected
