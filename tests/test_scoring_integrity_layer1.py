import unittest

from scripts.run_scoring_integrity_layer1 import normalize, scoreable_surface


class ScoringIntegrityTests(unittest.TestCase):
    def test_reasoning_only_is_no_answer(self) -> None:
        surface, unclosed, has_reasoning = scoreable_surface("<think>Useful facts but no close")
        self.assertEqual(surface, "")
        self.assertTrue(unclosed)
        self.assertTrue(has_reasoning)

    def test_closed_reasoning_is_removed(self) -> None:
        surface, unclosed, has_reasoning = scoreable_surface("<think>hidden</think>\nFinal answer.")
        self.assertEqual(surface, "Final answer.")
        self.assertFalse(unclosed)
        self.assertTrue(has_reasoning)

    def test_normalization_folds_diacritics_and_dashes(self) -> None:
        self.assertEqual(normalize("Forlì 600–900"), "forli 600-900")


if __name__ == "__main__":
    unittest.main()
