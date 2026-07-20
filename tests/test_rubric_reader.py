from src.analysis.rubric_reader import read_scores


def test_multi_digit_question_numbers_are_not_parsed_as_q1(tmp_path):
    scores_path = tmp_path / "scores.md"
    scores_path.write_text(
        """# Rubric Scores — iterative

| Question | Score | Notes |
|---|---:|---|
| Q1 — First | 1.0 | first note |
| Q10 — Tenth | 0.0 | tenth note |
| Q11 — Eleventh | 0.5 | eleventh note |
| Q12 — Twelfth | 1.0 | twelfth note |
| Q13 — Thirteenth | 1.0 | thirteenth note |

""",
        encoding="utf-8",
    )

    result = read_scores(str(scores_path))

    assert result["scores"] == {
        "Q1": 1.0,
        "Q10": 0.0,
        "Q11": 0.5,
        "Q12": 1.0,
        "Q13": 1.0,
    }
    assert result["notes"]["Q1"] == "first note"
    assert result["notes"]["Q13"] == "thirteenth note"
