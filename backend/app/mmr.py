from typing import List, Tuple
import numpy as np


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
    return float(np.dot(a, b) / denom)


def mmr(
    query_vec: np.ndarray,
    candidate_vectors: List[np.ndarray],
    candidate_indices: List[int],
    k: int = 8,
    lambda_mult: float = 0.7,
) -> List[int]:
    selected: List[int] = []
    candidate_set = set(candidate_indices)

    # Precompute similarities to query
    sim_to_query = {i: cosine_sim(query_vec, v) for i, v in zip(candidate_indices, candidate_vectors)}

    while len(selected) < min(k, len(candidate_indices)):
        best_i = None
        best_score = -1e9
        for i in candidate_set:
            if not selected:
                score = sim_to_query[i]
            else:
                redundancy = max(cosine_sim(candidate_vectors[candidate_indices.index(i)], candidate_vectors[candidate_indices.index(j)]) for j in selected)
                score = lambda_mult * sim_to_query[i] - (1 - lambda_mult) * redundancy
            if score > best_score:
                best_score = score
                best_i = i
        if best_i is None:
            break
        selected.append(best_i)
        candidate_set.remove(best_i)
    return selected


