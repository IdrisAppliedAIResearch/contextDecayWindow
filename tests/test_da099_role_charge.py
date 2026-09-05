from analysis.da009_role_pattern import append_role_pair, role_pattern_pairs
from analysis.da099_role_charge import IncrementalRoleCharge


def _member(speaker: str, text: str) -> dict[str, str]:
    return {"speaker": speaker, "text": text}


def test_incremental_role_charge_matches_immutable_context() -> None:
    pairs = [
        [_member("user", "one"), _member("assistant", "two")],
        [_member("user", "three"), _member("assistant", "four")],
    ]
    context = role_pattern_pairs(pairs)
    indexed = IncrementalRoleCharge(context)
    additions = [
        [_member("user", "five")],
        [_member("tool", "six")],
        [_member("user", "seven"), _member("assistant", "eight")],
    ]
    for addition in additions:
        updated = append_role_pair(context, addition)
        expected = updated.chars - context.chars
        assert indexed.cost(addition) == expected
        assert indexed.cost(addition, commit=True) == expected
        context = updated
        assert indexed.chars == context.chars
