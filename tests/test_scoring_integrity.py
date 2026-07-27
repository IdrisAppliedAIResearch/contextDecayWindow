import unittest

from src.analysis.scoring_integrity import (
    ScoringIntegrityError,
    inspect_completeness,
    validate_score,
)


class ScoringIntegrityGateTests(unittest.TestCase):
    def test_reasoning_only_is_no_answer(self) -> None:
        result = inspect_completeness("<think>Substantive but unfinished")
        self.assertTrue(result.no_answer)
        self.assertTrue(result.unclosed_reasoning)

    def test_positive_no_answer_is_blocked(self) -> None:
        with self.assertRaisesRegex(ScoringIntegrityError, "NO_ANSWER"):
            validate_score(
                score=1.0,
                response="<think>Correct facts but no final answer",
                rationale="Credited the facts.",
            )

    def test_generation_cap_truncation_is_blocked(self) -> None:
        with self.assertRaisesRegex(ScoringIntegrityError, "Truncated"):
            validate_score(
                score=0.5,
                response="A partial final answer",
                rationale="One fact present.",
                generation_cap_hit=True,
            )

    def test_missing_rationale_is_blocked(self) -> None:
        with self.assertRaisesRegex(ScoringIntegrityError, "rationale"):
            validate_score(score=0.0, response="Wrong.", rationale="")

    def test_complete_zero_is_valid(self) -> None:
        result = validate_score(score=0.0, response="Wrong.", rationale="No facts.")
        self.assertFalse(result.no_answer)


if __name__ == "__main__":
    unittest.main()

