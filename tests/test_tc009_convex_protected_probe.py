from __future__ import annotations

from analysis.tc009_convex_protected_probe import disposition


def test_disposition_requires_joint_two_budget_result() -> None:
    good = {"combined": {"gains": 3, "losses": 1}, "targeted": {"gains": 1, "losses": 1}, "breadth": {"gains": 1, "losses": 0}, "breadth_identity": {"net_identities": 1}, "conversation_nets": {"a": 1, "b": 1, "c": 0, "d": 0}}
    cells = {"16000": good, "32000": {**good, "breadth_identity": {"net_identities": 0}}}
    assert disposition(cells)["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL"
    cells["32000"] = {**good, "breadth": {"gains": 0, "losses": 1}}
    assert disposition(cells)["status"] == "NO_POSITIVE_SIGNAL"
