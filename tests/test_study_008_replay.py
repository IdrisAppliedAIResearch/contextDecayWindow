from pathlib import Path

from src.analysis.study_008_replay import (
    FactRow,
    load_fact_rows,
    match_facts,
)


REPO = Path(__file__).resolve().parents[1]


def test_locked_key_parses_fourteen_unique_fact_rows():
    rows = load_fact_rows()
    assert len(rows) == 14
    assert len({row.fact_id for row in rows}) == 14
    assert {row.domain for row in rows} == {
        "civil",
        "art",
        "monetary",
        "marine",
    }


def test_fact_coverage_requires_every_term_in_a_row():
    rows = [
        FactRow(
            domain="art",
            fact_id="art_identity",
            terms=("Annunciation", "Melozzo", "1483"),
            source_turns=(55,),
        )
    ]
    assert match_facts("Annunciation by Melozzo", rows)["art"] == []
    assert match_facts(
        "The 1483 Annunciation by Melozzo",
        rows,
    )["art"] == ["art_identity"]


def test_atomic_delivery_rows_do_not_duplicate_locked_fact_rows():
    rows = load_fact_rows(
        REPO / "experiments/study_008/q_facts_key.md"
    )
    assert all("_" in row.fact_id for row in rows)
