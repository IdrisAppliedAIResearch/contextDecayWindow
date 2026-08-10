from __future__ import annotations

import numpy as np


def score_after_first_hits(
    *,
    query: np.ndarray,
    episodes: np.ndarray,
    hits: np.ndarray,
    query_weight: float,
    retention: float,
) -> np.ndarray:
    reinstated = episodes[hits].mean(axis=0)
    context = retention * query + (1.0 - retention) * reinstated
    context /= np.linalg.norm(context)
    cue = query_weight * query + (1.0 - query_weight) * context
    cue /= np.linalg.norm(cue)
    return episodes @ cue
