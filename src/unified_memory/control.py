"""Independent source-matched chronological comparator. No treatment imports."""
import numpy as np


def cosine_matrix(vectors):
    matrix = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if not np.isfinite(matrix).all() or np.any(norms == 0):
        raise ValueError("Nonfinite or zero vector")
    return matrix / norms


def select(ids, vectors, query_vector):
    q = np.asarray(query_vector, dtype=np.float64)
    if not np.isfinite(q).all() or not np.linalg.norm(q):
        raise ValueError("Nonfinite or zero query vector")
    scores = cosine_matrix(vectors) @ (q / np.linalg.norm(q))
    return {key for key, value in zip(ids, scores, strict=True) if value >= .48}
