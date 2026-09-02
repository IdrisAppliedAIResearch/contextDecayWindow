import numpy as np
from pathlib import Path

from analysis.da013_transfer import _training


def test_da004_training_population_is_exact() -> None:
    repository_root = Path.cwd()
    matrix, labels = _training(
        repository_root / "experiments/components/biological_memory/da_004/artifacts/preflight/blind_perturbations.jsonl.gz",
        repository_root / "experiments/components/biological_memory/da_004/artifacts/result/edge_labels.jsonl.gz",
    )
    assert matrix.shape == (25_941, 73)
    assert labels.shape == (25_941,)
    assert int(labels.sum()) == 57
    assert np.isfinite(matrix).all()
