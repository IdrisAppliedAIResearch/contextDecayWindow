from itertools import combinations

from src.analysis.q11_achievability import (
    AtomicItem,
    Episode,
    Solution,
    best_solution,
    exact_payload_cost,
    exact_solutions,
    greedy_solution,
    nonempty_fixed_cost,
    solution_record,
)
from src.memory.context_builder import render_episode_element
from src.memory.context_matched_stm import render_stm_payload


def make_episode(
    episode_id: str,
    turn: int,
    mask: int,
    text: str,
) -> Episode:
    renderable = {
        "id": episode_id,
        "turn_number": turn,
        "user_message": text,
        "assistant_message": "",
    }
    return Episode(
        id=episode_id,
        turn_number=turn,
        user_message=text,
        assistant_message="",
        coverage_mask=mask,
        element_chars=len(render_episode_element(renderable)),
    )


def brute_force(
    episodes: tuple[Episode, ...],
    minimum_fact_count: int,
) -> tuple[int, tuple[int, ...]]:
    candidates = []
    for size in range(len(episodes) + 1):
        for indexes in combinations(range(len(episodes)), size):
            mask = 0
            for index in indexes:
                mask |= episodes[index].coverage_mask
            if mask.bit_count() < minimum_fact_count:
                continue
            solution = Solution(
                additive_chars=sum(
                    episodes[index].additive_chars for index in indexes
                ),
                episode_indexes=indexes,
            )
            candidates.append(
                (
                    exact_payload_cost(solution, episodes),
                    len(indexes),
                    tuple(
                        (episodes[index].turn_number, episodes[index].id)
                        for index in indexes
                    ),
                    mask,
                    indexes,
                )
            )
    best = min(candidates)
    return best[3], best[4]


def test_dynamic_program_matches_exhaustive_subset_minimum() -> None:
    episodes = (
        make_episode("a", 1, 0b00011, "short"),
        make_episode("b", 2, 0b00110, "somewhat longer"),
        make_episode("c", 3, 0b11100, "compact"),
        make_episode("d", 4, 0b11001, "longer competing episode"),
        make_episode("e", 5, 0b10000, "x"),
    )
    target_mask = 0b11111
    solutions = exact_solutions(episodes, target_mask)
    exact = best_solution(
        solutions,
        episodes,
        minimum_fact_count=4,
    )
    assert exact is not None

    expected_mask, expected_indexes = brute_force(episodes, 4)
    assert exact[0] == expected_mask
    assert exact[1].episode_indexes == expected_indexes


def test_additive_cost_matches_complete_renderer() -> None:
    episodes = (
        make_episode("a", 1, 0b01, "alpha"),
        make_episode("b", 2, 0b10, "beta"),
    )
    solution = Solution(
        additive_chars=sum(row.additive_chars for row in episodes),
        episode_indexes=(0, 1),
    )
    payload = render_stm_payload(
        [],
        [episode.as_renderable() for episode in episodes],
    )

    assert exact_payload_cost(solution, episodes) == len(payload)
    assert nonempty_fixed_cost() > 0


def test_greedy_is_an_upper_bound_on_exact_solution() -> None:
    episodes = (
        make_episode("a", 1, 0b00011, "short"),
        make_episode("b", 2, 0b00110, "somewhat longer"),
        make_episode("c", 3, 0b11100, "compact"),
        make_episode("d", 4, 0b11001, "longer competing episode"),
    )
    solutions = exact_solutions(episodes, 0b11111)
    exact = best_solution(
        solutions,
        episodes,
        minimum_fact_count=4,
    )
    greedy = greedy_solution(
        episodes,
        0b11111,
        minimum_fact_count=4,
    )
    assert exact is not None
    assert greedy is not None

    assert exact_payload_cost(
        exact[1], episodes
    ) <= exact_payload_cost(greedy[1], episodes)


def test_atomic_item_bit_is_stable() -> None:
    item = AtomicItem(index=3, domain="test", item="x", needle="x")

    assert item.bit == 0b1000


def test_domain_record_preserves_incidental_cross_domain_coverage() -> None:
    items = (
        AtomicItem(index=0, domain="a", item="alpha", needle="alpha"),
        AtomicItem(index=1, domain="b", item="beta", needle="beta"),
    )
    episode = make_episode("a", 1, 0b11, "alpha beta")
    solution = Solution(
        additive_chars=episode.additive_chars,
        episode_indexes=(0,),
    )

    record = solution_record(
        0b01,
        solution,
        (episode,),
        items,
        objective_mask=0b01,
    )

    assert record["fact_count"] == 1
    assert record["payload_fact_count"] == 2
    assert record["covered_items"] == [
        {"domain": "a", "item": "alpha"},
        {"domain": "b", "item": "beta"},
    ]
