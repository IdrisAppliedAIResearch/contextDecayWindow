from __future__ import annotations

import numpy as np

from analysis.tc010_study import disposition, qualified_order


class Episode:
    def __init__(self, identity: str) -> None:
        self.identity = identity


def _cell(good: bool, neutral: bool = False) -> dict:
    if neutral:
        return {"combined": {"gains": 1, "losses": 1, "net": 0}, "targeted": {"gains": 1, "losses": 1, "net": 0}, "breadth": {"gains": 1, "losses": 1, "net": 0}, "breadth_identity": {"net_identities": 0}, "conversation_nets": {"a": 0, "b": 0, "c": 0, "d": 0}}
    return {"combined": {"gains": 3 if good else 1, "losses": 1 if good else 3, "net": 2 if good else -2}, "targeted": {"gains": 1, "losses": 1, "net": 0}, "breadth": {"gains": 2 if good else 0, "losses": 0 if good else 2, "net": 2 if good else -2}, "breadth_identity": {"net_identities": 2 if good else -2}, "conversation_nets": {"a": 1 if good else -1, "b": 1, "c": 0, "d": 0}}


def test_qualified_order_stays_inside_pool_and_updates() -> None:
    episodes = [Episode(str(index)) for index in range(8)]
    similarity = np.eye(8, dtype=np.float32)
    similarity[2, 0] = similarity[0, 2] = 0.8
    similarity[1, 0] = similarity[0, 1] = 0.2
    order, scores, cutoff = qualified_order(episodes, tuple(range(8)), ("0",), similarity)
    assert cutoff == 2
    assert order == (1,)
    assert scores == (np.float32(0.2),)


def test_disposition_branches_are_reachable() -> None:
    good = {"16000": _cell(True), "32000": _cell(True)}
    assert disposition(good, {"16000": 3, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "QUALIFIED_SPREAD_WORKS"
    mixed = {"16000": _cell(True), "32000": _cell(True, neutral=True)}
    assert disposition(mixed, {"16000": 3, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "QUALIFIED_SPREAD_CARRIES_SIGNAL"
    assert disposition(good, {"16000": 1, "32000": 3}, {"16000": 2, "32000": 2})["status"] == "CONTROL_FAILURE"
