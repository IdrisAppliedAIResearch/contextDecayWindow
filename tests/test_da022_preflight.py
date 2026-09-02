from analysis.da022_preflight import SOURCE_SHA256


def test_da022_source_is_bound_to_da021_selection() -> None:
    assert SOURCE_SHA256 == "2e1eb8795f9f8a06ec5900ff7297a6b962a5257c56fac2f8ac1925954c17aed9"

