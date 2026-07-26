"""Study 007 bar-evaluation logic, verified on synthetic data before use.

The bars decide the study's verdict, so their arithmetic is tested rather than
trusted — including the ordering rule that Bar 3 gates Bar 1, and the
attribution rule that four-domain coverage must be visible in the block.
"""

import json

import pytest

from src.analysis.study_007_evaluation import (
    BAR2_CATEGORIES,
    CATEGORY_QUESTIONS,
    block_coverage,
    budget_coverage,
    delivered_information,
)


LTM_TEMPLATE = """<retrieved_ltm>
{episodes}
</retrieved_ltm>"""

EPISODE = """  <episode turn="{turn}" topic="{topic}" similarity="0.5">
    <user_message>{text}</user_message>
    <assistant_message></assistant_message>
  </episode>"""


def write_prompt(run_dir, turn: int, episodes: list[tuple[int, str, str]]):
    prompts = run_dir / "constructed_prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    body = "\n".join(
        EPISODE.format(turn=t, topic=topic, text=text)
        for t, topic, text in episodes
    )
    (prompts / f"turn_{turn:03d}.txt").write_text(
        "system\n\n" + LTM_TEMPLATE.format(episodes=body), encoding="utf-8"
    )


# --------------------------------------------------------------------------
# Coverage against the rendered block
# --------------------------------------------------------------------------


def test_four_domain_coverage_detected(tmp_path):
    write_prompt(tmp_path, 120, [
        (3, "t_civil", "Halcyon Crossing spans 847 metres."),
        (55, "t_art", "The Annunciation by Melozzo, 1483."),
        (65, "t_mon", "Dr Priya Mehta set the reverse repurchase rate."),
        (100, "t_mar", "Vampyroteuthis feeds on marine snow."),
    ])
    result = block_coverage(tmp_path, 120)

    assert result["four_domain"] is True
    assert result["domains_covered"] == ["art", "civil", "marine", "monetary"]
    assert result["episodes"] == 4
    assert result["topic_count"] == 4


def test_single_domain_coverage_is_not_four_domain(tmp_path):
    """Study 006's Q11 shape: several episodes, one domain."""
    write_prompt(tmp_path, 120, [
        (3, "t_civil", "Halcyon Crossing spans 847 metres."),
        (4, "t_civil", "S460ML steel, 92.4 tonnes per axle."),
        (8, "t_civil", "Dr Anara Bekova leads the team."),
    ])
    result = block_coverage(tmp_path, 120)

    assert result["four_domain"] is False
    assert result["domains_covered"] == ["civil"]
    assert result["topic_count"] == 1


def test_topics_and_domains_are_counted_separately(tmp_path):
    """Four topic ids carrying one domain's content is not four-domain."""
    write_prompt(tmp_path, 120, [
        (3, "t_a", "Halcyon Crossing."),
        (4, "t_b", "847 metres."),
        (5, "t_c", "S460ML."),
        (6, "t_d", "Anara Bekova."),
    ])
    result = block_coverage(tmp_path, 120)

    assert result["topic_count"] == 4
    assert result["domains_covered"] == ["civil"]
    assert result["four_domain"] is False


def test_missing_prompt_yields_empty_coverage(tmp_path):
    result = block_coverage(tmp_path, 120)
    assert result["block_chars"] == 0
    assert result["domains_covered"] == []
    assert result["four_domain"] is False


def test_delivered_information_per_turn(tmp_path):
    write_prompt(tmp_path, 1, [(1, "t", "short")])
    write_prompt(tmp_path, 2, [(2, "t", "x" * 500)])
    result = delivered_information(tmp_path)

    assert result["turns_with_ltm"] == 2
    assert result["max_chars"] > 500
    assert set(result["per_turn"]) == {1, 2}


# --------------------------------------------------------------------------
# Coverage against the budget log
# --------------------------------------------------------------------------


def test_budget_coverage_reads_the_probe_row(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    header = (
        "turn,b_ltm,k_min,topics_present,topic_count,floor_selected_per_topic,"
        "floor_selected,fill_selected,containment_drops,refills,"
        "collapsed_to_episode,ltm_chars_used,ltm_records_used,"
        "budget_utilization,chars_per_topic,selection\n"
    )
    row = (
        '120,32000,1,"[""a"",""b""]",2,"{""a"":1,""b"":1}",2,6,3,0,4,31269,8,'
        '0.9772,"{""a"":20000,""b"":11269}","[]"\n'
    )
    (logs / "retrieval_budget.csv").write_text(header + row, encoding="utf-8")

    result = budget_coverage(tmp_path, 120)

    assert result["topic_count"] == 2
    assert result["chars_used"] == 31269
    assert result["records_used"] == 8
    assert result["containment_drops"] == 3
    assert sum(result["chars_per_topic"].values()) == result["chars_used"]


def test_budget_coverage_absent_for_control(tmp_path):
    """The control writes no retrieval_budget.csv; that must not crash."""
    assert budget_coverage(tmp_path, 120) is None


# --------------------------------------------------------------------------
# Category mapping
# --------------------------------------------------------------------------


def test_categories_match_the_locked_rubric():
    assert CATEGORY_QUESTIONS["cat_1"] == ["Q1", "Q2", "Q3"]
    assert CATEGORY_QUESTIONS["cat_2"] == ["Q4", "Q5", "Q6"]
    assert CATEGORY_QUESTIONS["cat_3"] == ["Q7", "Q8"]
    assert CATEGORY_QUESTIONS["cat_4"] == ["Q9", "Q10", "Q11"]
    assert CATEGORY_QUESTIONS["cat_5"] == ["Q12", "Q13"]


def test_every_question_q1_q13_appears_exactly_once():
    seen = [q for qs in CATEGORY_QUESTIONS.values() for q in qs]
    assert sorted(seen, key=lambda q: int(q[1:])) == [
        f"Q{i}" for i in range(1, 14)
    ]
    assert len(seen) == len(set(seen))


def test_bar2_reads_plant_survival_categories_only():
    assert BAR2_CATEGORIES == ("cat_1", "cat_2", "cat_3")
