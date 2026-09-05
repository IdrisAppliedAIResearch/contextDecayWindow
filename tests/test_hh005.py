from analysis.hh005_contexts import ARMS, EXPECTED, build_contexts


def test_semantic_da_v2_replays_and_respects_channels():
    for budget in ARMS:
        first = build_contexts(budget)
        assert first == build_contexts(budget)
        assert len(first["items"]) == EXPECTED
        for row in first["items"].values():
            detail = row["detail"]
            assert detail["semantic_chars"] <= budget // 2
            assert detail["derivative_chars"] <= budget // 2
            assert detail["derivative_source_ids"]
            assert not detail["aspect_v1_included"]
            assert len(detail["derivative_source_ids"]) == len(set(detail["derivative_source_ids"]))
