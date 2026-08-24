from __future__ import annotations

from types import SimpleNamespace

from analysis.tc009_dynamic_session import dynamic_session_order


def episode(index: int, session: str, session_order: int):
    return SimpleNamespace(
        identity=f"e{index}",
        pair=SimpleNamespace(
            session_id=session,
            session_order=session_order,
            pair_order=index,
        ),
    )


def test_penalized_session_can_still_win_consecutive_slots() -> None:
    episodes = (episode(0, "s1", 0), episode(1, "s1", 0), episode(2, "s2", 1))
    result = dynamic_session_order(episodes, (.90, .86, .82))
    assert result.order == (0, 1, 2)
    assert result.steps[1].session_count_before == 1
    assert result.steps[1].adjusted_score == .86 - .03


def test_accumulated_penalty_eventually_allows_overtake() -> None:
    episodes = (
        episode(0, "s1", 0),
        episode(1, "s1", 0),
        episode(2, "s1", 0),
        episode(3, "s2", 1),
    )
    result = dynamic_session_order(episodes, (.90, .86, .84, .82))
    assert result.order == (0, 1, 3, 2)
    assert result.steps[2].session_id == "s2"


def test_zero_lambda_is_dense_order() -> None:
    episodes = (episode(0, "s2", 1), episode(1, "s1", 0), episode(2, "s2", 1))
    result = dynamic_session_order(episodes, (.7, .9, .8), lambda_=0.0)
    assert result.order == (1, 2, 0)


def test_one_session_stays_dense_despite_accumulated_penalty() -> None:
    episodes = tuple(episode(index, "only", 0) for index in range(4))
    result = dynamic_session_order(episodes, (.7, .9, .8, .6))
    assert result.order == (1, 2, 0, 3)
    assert [step.session_count_before for step in result.steps] == [0, 1, 2, 3]
