from analysis.da008_analysis import allocate_links
from analysis.da008_compact_direct import compact_pairs, incremental_pair_cost


def test_allocator_rejects_duplicates_and_continues_after_overflow() -> None:
    members = {
        "direct": [{"speaker": "A", "text": "core"}],
        "big": [{"speaker": "A", "text": "x" * 20}],
        "small": [{"speaker": "A", "text": "ok"}],
    }
    context = compact_pairs([members["direct"]])
    small_cost = incremental_pair_cost(context, members["small"])
    budget = context.chars + small_cost
    edges = [{"neighbor_id": "direct"}, {"neighbor_id": "big"}, {"neighbor_id": "small"}, {"neighbor_id": "small"}]
    result = allocate_links(context, ["direct"], edges, members, budget)
    assert result["linked_ids"] == ["small"]
    assert result["linked_positions"] == [3]
    assert result["duplicate_skips"] == 2
    assert result["overflow_skips"] == 1
    assert result["total_chars"] == budget


def test_allocator_charges_new_speaker_once_across_links() -> None:
    members = {
        "direct": [{"speaker": "A", "text": "core"}],
        "one": [{"speaker": "B", "text": "first"}],
        "two": [{"speaker": "B", "text": "second"}],
    }
    context = compact_pairs([members["direct"]])
    result = allocate_links(context, ["direct"], [{"neighbor_id": "one"}, {"neighbor_id": "two"}], members, 100)
    assert result["linked_ids"] == ["one", "two"]
    assert result["linked_costs"][0] == len("@1=B") + len("1:first")
    assert result["linked_costs"][1] == len("1:second")
