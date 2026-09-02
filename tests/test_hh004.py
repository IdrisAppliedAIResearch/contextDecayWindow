import gc

from analysis.hh004_contexts import EXPECTED, build_contexts, render_members
from analysis.hh004_run import pilot_keys


def test_renderer_is_deterministic_and_member_delimited() -> None:
    values = [{"speaker": "A", "text": "first"},
              {"speaker": "B", "text": "second"}]
    rendered = render_members(values)
    assert rendered == render_members(values)
    assert rendered.count("<member index=") == 2
    assert "A: first" in rendered and "B: second" in rendered


def test_blind_population_and_pilot_are_locked() -> None:
    contexts = build_contexts()
    assert contexts["population"] == EXPECTED
    assert len(contexts["items"]) == EXPECTED
    keys = pilot_keys(contexts["items"])
    assert len(keys) == len(set(keys)) == 8


def test_build_does_not_change_gc_state() -> None:
    enabled = gc.isenabled()
    build_contexts()
    assert gc.isenabled() == enabled
