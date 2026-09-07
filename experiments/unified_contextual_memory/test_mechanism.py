import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import numpy as np
import pytest
from unified_memory.source import adapt, render, Unit
from unified_memory.encoder import Cache
from unified_memory.references import Reference
from unified_memory.retrieval import retrieve, Policy, Conflict


def fixture():
    units = tuple(Unit(str(i), "conversation", "s", i, "date", (f"D{i}",),
                       text, text, ("A",)) for i, text in enumerate((
                           "I interviewed at Northstar.", "I interviewed at Cedar.", "I accepted the offer.")))
    vectors = {"0": np.array([0., 1.]), "1": np.array([0., 1.]), "2": np.array([1., 0.])}
    refs = (Reference("r", "2", units[2].text, 0, ("the offer",)),)
    return units, vectors, refs


def run(*, conflicts=(), refs=None, contexts=None, contextual=None):
    units, vectors, original_refs = fixture()
    return retrieve(units, vectors, contextual or vectors,
                    contexts or {u.id: [u.id] for u in units},
                    original_refs if refs is None else refs,
                    {"r": np.array([0., 1.]), "r0": np.array([1., 0.])},
                    np.array([1., 0.]), Policy(.99, .99, .99), conflicts=conflicts)


def test_two_candidates_preserved_without_forced_resolution():
    result = run()
    assert result["selected"] == ["0", "1", "2"]
    assert len(result["bindings"]) == 2
    assert all(b["status"] == "unresolved" for b in result["bindings"])
    assert result["direct"] == ["2"]


def test_self_match_cannot_count_as_support_or_antecedent():
    result = run(refs=())
    assert result["unresolved_support"] == ["2"]
    assert result["selected"] == ["2"]
    assert result["bindings"] == []


def test_contextual_hit_recovers_low_query_similarity_support():
    units, vectors, _ = fixture()
    contexts = {u.id: [u.id] for u in units}
    contexts["0"] = ["0", "1"]
    contextual = dict(vectors, **{"0": np.array([1., 0.])})
    result = run(refs=(), contexts=contexts, contextual=contextual)
    assert result["selected"] == ["0", "1", "2"]
    assert "context-support:0" in result["admissions"]["1"]


def test_future_encoding_context_is_rejected():
    with pytest.raises(ValueError, match="knowledge horizon"):
        run(contexts={"0": ["0"], "1": ["1"], "2": ["2", "unavailable"]})


def test_rejected_binding_does_not_admit_or_continue_source():
    units, _, refs = fixture()
    cycle = refs + (Reference("r0", "0", units[0].text, 0, ("I",)),)
    result = run(conflicts=(Conflict("r", "0", ("2",), "explicit-test-incompatibility"),), refs=cycle)
    assert result["selected"] == ["1", "2"]
    assert not any(b["reference"] == "r0" for b in result["bindings"])


def test_cycle_terminates_and_selection_is_chronological():
    units, _, refs = fixture()
    cycle = refs + (Reference("r0", "0", units[0].text, 0, ("I",)),)
    result = run(refs=cycle)
    assert result["operations"] <= result["operation_bound"]
    assert result["selected"] == ["0", "1", "2"]
    assert "ANSWER_COMPLETE" not in result["stop"]


def test_caption_fidelity_and_escape():
    source = {"speaker_a": "A", "speaker_b": "B", "session_1_date_time": "today",
              "session_1": [{"speaker": "A", "dia_id": "D1:1", "text": "Look <here>", "blip_caption": "Do not leave"}]}
    units = adapt(source, "c")
    assert "Do not leave" in units[0].text and "Do not leave" not in units[0].historical_text
    assert "&lt;here&gt;" in render(units, {units[0].id})
    with pytest.raises(ValueError):
        adapt(dict(source, answer="forbidden"), "c")


def test_cache_rejects_overwrite_and_readonly_miss(tmp_path):
    path = tmp_path / "vectors.db"
    cache = Cache(path)
    vector = np.ones(1024, dtype=np.float32)
    cache.put({"text": "source"}, vector)
    with pytest.raises(ValueError, match="overwrite"):
        cache.put({"text": "source"}, vector * 2)
    cache.close()
    cache = Cache(path, readonly=True)
    assert np.array_equal(cache.get({"text": "source"}), vector)
    with pytest.raises(KeyError):
        cache.get({"text": "missing"})
    cache.close()
