import numpy as np

from analysis.da012_analysis import carrier_label, grouped_carrier_predictions


def test_carrier_label_requires_missing_direct_dialogue_overlap() -> None:
    assert carrier_label({"a", "b"}, {"b", "c"})
    assert not carrier_label({"a", "b"}, {"c"})
    assert not carrier_label({"a"}, set())


def test_grouped_carrier_predictions_score_all_target_rows_but_evaluate_incomplete_only() -> None:
    rows = []
    groups = ("a", "b", "c")
    for group_index, group in enumerate(groups):
        for index in range(8):
            carrier = index % 2 == 0
            rows.append({"sample_id": group, "carrier": carrier, "carrier_population": index < 6,
                         "features": {name: float(carrier) + group_index * .01 for name in __import__("analysis.da004_pack_features", fromlist=["FEATURES"]).FEATURES}})
    predictions, metrics = grouped_carrier_predictions(rows)
    assert len(predictions) == 24
    assert np.isfinite(predictions).all()
    assert metrics["n"] == 18
    assert all(cell["overlap"] == 0 and cell["test_all"] == 8 and cell["test_evaluable"] == 6 for cell in metrics["by_conversation"].values())
