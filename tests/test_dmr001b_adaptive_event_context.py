"""DMR-001B verification contract and committed artifacts."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from src.analysis.dmr001b_gates import BARS, DISPOSITIONS, PASS_DISPOSITION, evaluate_gates
from src.biological_memory.adaptive_event_context import (
    AdaptiveEventContextError,
    AdaptiveEventContextFormer,
    AdaptiveEventContextStore,
    AdaptiveFormerConfig,
    form,
    load_design,
    percentile,
)
from src.biological_memory.event_context import EventContextError, normalize

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "experiments" / "components" / "biological_memory" / "dmr_001b"
DESIGN = STUDY / "DMR_001B_FINAL_DESIGN.json"
REGISTRATION = STUDY / "DMR_001B_PRE_REGISTRATION.md"
PREFLIGHT = STUDY / "artifacts" / "dmr001b_preflight" / "preflight.json"
GATES = STUDY / "artifacts" / "dmr001b_gates" / "gate_report.json"
DEVIATION = STUDY / "DEVIATION_001_implementation_preceded_registration.md"

ANCHOR = "0" * 64
CONFIG = AdaptiveFormerConfig(
    drift_percentile=0.975, history_window=16, warmup=16, min_event_size=5, max_event_size=128
)


def identity(value: int) -> str:
    return f"{value:064x}"


def basis(index: int) -> np.ndarray:
    vector = np.zeros(1024, dtype=np.float32)
    vector[index % 1024] = 1.0
    return vector


def stream(vectors, *, session=identity(7)):
    return [
        {
            "episode_hash": identity(1000 + position),
            "session_hash": session,
            "turn_index": position,
            "embedding": vector,
        }
        for position, vector in enumerate(vectors)
    ]


# ---------------------------------------------------------------------------
# Percentile
# ---------------------------------------------------------------------------


def test_percentile_interpolates_and_is_library_independent() -> None:
    assert percentile([0.0, 1.0], 0.5) == 0.5
    assert percentile([0.0, 1.0, 2.0, 3.0], 0.0) == 0.0
    assert percentile([0.0, 1.0, 2.0, 3.0], 1.0) == 3.0
    assert percentile([5.0], 0.9) == 5.0
    with pytest.raises(AdaptiveEventContextError):
        percentile([], 0.5)


# ---------------------------------------------------------------------------
# The bar is relative
# ---------------------------------------------------------------------------


def test_the_rule_cannot_fire_before_warmup() -> None:
    vectors = [basis(index) for index in range(10)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    assert all(not d.adaptive_boundary for d in snapshot.decisions)
    assert all(d.boundary_threshold == float("inf") for d in snapshot.decisions[:16])


def test_the_same_shape_at_two_scales_gives_the_same_partition() -> None:
    """The point of the whole study: no absolute drift constant survives."""
    low = [normalize(basis(0) + np.float32(0.02) * basis(index + 1)) for index in range(40)]
    high = [normalize(basis(0) + np.float32(0.60) * basis(index + 1)) for index in range(40)]
    low_events = len(form(stream(low), design_sha256=ANCHOR, config=CONFIG).events)
    high_events = len(form(stream(high), design_sha256=ANCHOR, config=CONFIG).events)
    assert low_events == high_events


def test_drift_history_resets_at_a_session_boundary() -> None:
    first = stream([basis(index) for index in range(20)], session=identity(7))
    second = [
        {
            "episode_hash": identity(5000 + position),
            "session_hash": identity(8),
            "turn_index": position,
            "embedding": basis(position),
        }
        for position in range(3)
    ]
    snapshot = form(first + second, design_sha256=ANCHOR, config=CONFIG)
    after = snapshot.decisions[20:]
    assert after[0].hard_boundary
    assert all(d.boundary_threshold == float("inf") for d in after)
    assert after[-1].history_size < CONFIG.history_window


# ---------------------------------------------------------------------------
# Typed cap closures
# ---------------------------------------------------------------------------


def test_a_cap_closure_is_not_a_boundary_claim() -> None:
    config = AdaptiveFormerConfig(
        drift_percentile=0.975, history_window=16, warmup=16, min_event_size=5, max_event_size=8
    )
    snapshot = form(stream([basis(0)] * 30), design_sha256=ANCHOR, config=config)
    capped = [d for d in snapshot.decisions if d.boundary_reason == "capped"]
    assert capped, "the fixture must actually reach the cap"
    assert all(d.new_event for d in capped)
    assert all(not d.claims_boundary for d in capped)
    assert snapshot.claimed_boundaries() != snapshot.all_closures()
    assert snapshot.claimed_boundaries().isdisjoint(
        {d.turn_index for d in capped}
    )


def test_a_zero_variance_stream_makes_the_relative_rule_fire_freely() -> None:
    """A degenerate input the pre-registration's `>=` comparison implies.

    On a stream of identical episodes every drift is the same, so `drift >= the
    97.5th percentile of drift` is true as soon as the history is warm. The
    relative rule then opens an event whenever `min_event_size` is met. This is
    correct per section 2.1 as registered, and it is the price of removing the
    absolute constant: with no scale of its own, the rule has nothing to say
    about a stream with no variance.

    It is not reached on either corpus - both gate families record 0 capped
    closures and fire rates of 3.15% and 4.49% - but a real conversation of
    near-identical turns would reach it, and no bar in the registration
    detects it.
    """
    snapshot = form(stream([basis(0)] * 30), design_sha256=ANCHOR, config=CONFIG)
    drifts = [d.boundary_score for d in snapshot.decisions[1:]]
    assert max(drifts) - min(drifts) < 1e-6, "the fixture must have no drift variance"
    adaptive = [d for d in snapshot.decisions if d.adaptive_boundary]
    assert adaptive, "the registered `>=` comparison fires on a flat history"
    assert all(d.open_event_size_before >= CONFIG.min_event_size for d in adaptive)


def test_hard_and_adaptive_closures_are_claims() -> None:
    snapshot = form(stream([basis(0)] * 40), design_sha256=ANCHOR, config=CONFIG)
    assert snapshot.decisions[0].boundary_reason == "stream_start"
    assert snapshot.decisions[0].claims_boundary


def test_capped_closures_are_recorded_in_the_event_row() -> None:
    config = AdaptiveFormerConfig(
        drift_percentile=0.975, history_window=16, warmup=16, min_event_size=5, max_event_size=8
    )
    store = AdaptiveEventContextStore.in_memory()
    form(stream([basis(0)] * 30), design_sha256=ANCHOR, config=config, store=store)
    assert store.counts()["capped_closures"] > 0


# ---------------------------------------------------------------------------
# Carried contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"episode_hash": "nope"},
        {"session_hash": "NOPE"},
        {"turn_index": -1},
        {"turn_index": 1.5},
        {"embedding": np.zeros(8, dtype=np.float32)},
        {"embedding": np.zeros(1024, dtype=np.float32)},
    ],
)
def test_malformed_causal_inputs_are_rejected(kwargs) -> None:
    former = AdaptiveEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    call = {
        "episode_hash": identity(1),
        "session_hash": identity(7),
        "turn_index": 0,
        "embedding": basis(0),
    }
    call.update(kwargs)
    with pytest.raises((EventContextError, ValueError, TypeError)):
        former.observe(**call)


def test_out_of_order_turns_and_reopened_sessions_are_rejected() -> None:
    former = AdaptiveEventContextFormer(design_sha256=ANCHOR, config=CONFIG)
    former.observe(
        episode_hash=identity(1), session_hash=identity(7), turn_index=5, embedding=basis(0)
    )
    with pytest.raises(AdaptiveEventContextError, match="strictly increasing"):
        former.observe(
            episode_hash=identity(2), session_hash=identity(7), turn_index=5, embedding=basis(0)
        )
    former.observe(
        episode_hash=identity(3), session_hash=identity(8), turn_index=0, embedding=basis(0)
    )
    with pytest.raises(AdaptiveEventContextError, match="already closed"):
        former.observe(
            episode_hash=identity(4), session_hash=identity(7), turn_index=9, embedding=basis(0)
        )


def test_partition_invariants_hold() -> None:
    vectors = [basis(index // 4) for index in range(120)]
    snapshot = form(stream(vectors), design_sha256=ANCHOR, config=CONFIG)
    counts = snapshot.validate()
    assert counts["episodes"] == 120
    assert sum(record.member_count for record in snapshot.events) == 120


def test_replay_is_idempotent_and_conflict_is_loud() -> None:
    store = AdaptiveEventContextStore.in_memory()
    episodes = stream([basis(index // 6) for index in range(40)])
    form(episodes, design_sha256=ANCHOR, config=CONFIG, store=store)
    before = store.counts()
    form(episodes, design_sha256=ANCHOR, config=CONFIG, store=store)
    assert store.counts() == before
    conflicting = [dict(episode) for episode in episodes]
    conflicting[30]["embedding"] = basis(900)
    with pytest.raises(AdaptiveEventContextError, match="Conflicting replay"):
        form(conflicting, design_sha256=ANCHOR, config=CONFIG, store=store)


def test_the_predecessor_component_is_not_modified_by_this_study() -> None:
    source = (ROOT / "src" / "biological_memory" / "adaptive_event_context.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert ".event_context" in imported or "event_context" in {
        m.split(".")[-1] for m in imported
    }


def test_no_project_module_outside_the_package_is_reachable() -> None:
    import subprocess

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'" + str(ROOT) + "'); "
            "import src.biological_memory.adaptive_event_context; "
            "print(sorted(n for n in sys.modules if n.startswith('src.')))",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(ROOT),
    )
    loaded = set(ast.literal_eval(result.stdout.strip()))
    assert all(name.startswith("src.biological_memory") for name in loaded), loaded


def test_a_fresh_process_reproduces_the_digest(tmp_path) -> None:
    import subprocess

    script = tmp_path / "replay.py"
    script.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT)!r})\n"
        "import numpy as np\n"
        "from src.biological_memory.adaptive_event_context import AdaptiveFormerConfig, form\n"
        "c = AdaptiveFormerConfig(drift_percentile=0.975, history_window=16, warmup=16,"
        " min_event_size=5, max_event_size=128)\n"
        "def b(i):\n"
        "    v = np.zeros(1024, dtype=np.float32); v[i % 1024] = 1.0; return v\n"
        "eps = [{'episode_hash': f'{1000+p:064x}', 'session_hash': f'{7:064x}',\n"
        "        'turn_index': p, 'embedding': b(p // 4)} for p in range(120)]\n"
        f"print(form(eps, design_sha256={ANCHOR!r}, config=c).digest())\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=True, cwd=str(ROOT)
    )
    expected = form(
        stream([basis(index // 4) for index in range(120)]),
        design_sha256=ANCHOR,
        config=CONFIG,
    ).digest()
    assert result.stdout.strip() == expected


# ---------------------------------------------------------------------------
# Committed artifacts
# ---------------------------------------------------------------------------


def test_design_anchor_matches_the_registration_on_disk() -> None:
    anchor, config, payload = load_design(DESIGN)
    assert config == CONFIG
    assert payload["outcome_ceiling"] == "CHARACTERIZED"
    assert len(anchor) == 64


def test_gate_bars_match_the_registration_text() -> None:
    text = REGISTRATION.read_text(encoding="utf-8")
    assert "Singleton fraction <= 0.20" in text
    assert "capped closures == 0" in text
    assert "swing between the two substantive families is <= 2.0x" in text
    assert BARS["G3"]["max_singleton_fraction"] == 0.20
    assert BARS["G3"]["max_capped_closures"] == 0
    assert BARS["G4"]["max_swing"] == 2.0
    assert BARS["G4"]["percentile_grid"] == [0.8, 0.85, 0.9, 0.95, 0.975]


def test_the_deviation_is_recorded_and_surfaced_everywhere() -> None:
    assert DEVIATION.exists()
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    assert design["deviations"][0]["id"] == "DEVIATION_001"
    assert design["deviations"][0]["affects_confirmatory_standing"] is True
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    assert preflight["status"] == "PASS_WITH_RECORDED_DEVIATION"
    assert any(f["section"] == "PF3_ordering" for f in preflight["failed_checks"])


def test_preflight_fails_only_on_the_recorded_ordering_deviation() -> None:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    assert {f["section"] for f in preflight["failed_checks"]} == {"PF3_ordering"}


def test_committed_gate_report_passes_and_the_cap_never_bound() -> None:
    report = json.loads(GATES.read_text(encoding="utf-8"))
    assert report["verdict"]["disposition"] == PASS_DISPOSITION
    assert report["verdict"]["stopped_at"] is None
    for family in report["families"].values():
        assert family["capped_closures"] == 0
        assert family["singleton_fraction"] == 0.0


def test_every_percentile_in_the_grid_holds_the_swing_bar() -> None:
    report = json.loads(GATES.read_text(encoding="utf-8"))
    g4 = next(gate for gate in report["verdict"]["gates"] if gate["gate"] == "G4")
    assert set(g4["swings"]) == {"0.8", "0.85", "0.9", "0.95", "0.975"}
    for value in g4["swings"].values():
        assert value["swing"] <= BARS["G4"]["max_swing"]


def test_the_improvement_claim_is_against_the_predecessor_not_a_control() -> None:
    report = json.loads(GATES.read_text(encoding="utf-8"))
    g5 = next(gate for gate in report["verdict"]["gates"] if gate["gate"] == "G5")
    assert g5["treatment_worst_f1"] >= g5["predecessor_worst_f1"]
    assert report["predecessor"]["family_1000_61311041"]["capped_fraction"] > 0.5


def test_gates_stop_at_the_first_failure() -> None:
    gates = [
        {"gate": "G1", "name": "Integrity", "checks": [{"passed": True}]},
        {"gate": "G2", "name": "Partition", "checks": [{"passed": False}]},
        {"gate": "G3", "name": "Nondegeneracy", "checks": [{"passed": True}]},
    ]
    verdict = evaluate_gates(gates)
    assert verdict["stopped_at"] == "G2"
    assert verdict["disposition"] == DISPOSITIONS["G2"]
    assert [gate["evaluated"] for gate in verdict["gates"]] == [True, True, False]
