from analysis.tc007_reachability import BANDS, SIGNAL_ALPHA, WORKS_ALPHA, clears, generate


def test_registered_family_and_sham_bands() -> None:
    assert WORKS_ALPHA == 0.01 / 12
    assert SIGNAL_ALPHA == 0.10 / 12
    assert BANDS == {
        16_000: {"combined": 2, "breadth": 0, "targeted": 2},
        32_000: {"combined": 0, "breadth": 0, "targeted": 0},
    }


def test_each_direction_and_neutral_are_reachable(tmp_path) -> None:
    result = generate(tmp_path / "reachability.json")
    assert result["status"] == "PASS"
    for budget in result["cells"].values():
        for endpoint in budget.values():
            assert endpoint["treatment_works_reachable"]
            assert endpoint["control_works_reachable"]
            assert endpoint["neutral_reachable"]


def test_band_is_strict() -> None:
    assert not clears(2, 0, 2, WORKS_ALPHA)
    assert clears(20, 0, 2, WORKS_ALPHA)
