from analysis.da009_analysis import allocate_role_links
from analysis.da009_role_pattern import role_pattern_pairs


def test_role_allocator_continues_after_overflow_and_rejects_duplicates() -> None:
    members = {
        "direct": [{"speaker": "A", "text": "core"}, {"speaker": "B", "text": "base"}],
        "big": [{"speaker": "A", "text": "x" * 30}, {"speaker": "B", "text": "y" * 30}],
        "small": [{"speaker": "A", "text": "ok"}, {"speaker": "B", "text": "yes"}],
    }
    context = role_pattern_pairs([members["direct"]])
    budget = context.chars + len("ok\nyes")
    result = allocate_role_links(context, ["direct"], [{"neighbor_id": "direct"}, {"neighbor_id": "big"},
                                                       {"neighbor_id": "small"}, {"neighbor_id": "small"}], members, budget)
    assert result["linked_ids"] == ["small"]
    assert result["linked_positions"] == [3]
    assert result["overflow_skips"] == 1
    assert result["duplicate_skips"] == 2
    assert result["total_chars"] == budget
