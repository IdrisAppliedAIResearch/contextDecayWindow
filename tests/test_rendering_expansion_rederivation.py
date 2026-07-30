from src.analysis.rendering_expansion_rederivation import (
    _containment_check,
    _n_cap_check,
)


def test_q4_rank_check_does_not_open_post_fix_packing():
    result = _n_cap_check()

    assert result["status"] == "PASS"
    assert result["turn_55_rank"] == 27
    assert result["turn_55_within_cap"]
    assert not result["post_fix_packing_opened"]


def test_containment_remains_keyed_by_source_episode_identity():
    result = _containment_check()

    assert result["status"] == "PASS"
    assert result["selected_episode_ids"] == ["replacement"]
    assert result["containment_drops"] == 1

