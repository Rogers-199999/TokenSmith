from typing import List

from src.duplicate_detector import DuplicateDetector


def deduplicate_retrieved_chunk_indices(
    chunks: List[str],
    ordered: List[int],
    top_k: int,
    threshold: float = 0.8,
    pool_multiplier: int = 3,
) -> List[int]:
    """
    Duplicate-aware filtering over ranked chunk indices.

    Parameters
    ----------
    chunks:
        Full chunk text list.
    ordered:
        Ranked chunk indices from the retriever/ranker.
    top_k:
        Number of final chunks to keep.
    threshold:
        Near-duplicate Jaccard similarity threshold.
    pool_multiplier:
        Expand candidate pool beyond top_k so filtering still leaves enough chunks.
    """
    detector = DuplicateDetector()
    selected: List[int] = []

    candidate_pool_size = max(top_k * pool_multiplier, top_k)
    pool = ordered[:candidate_pool_size]

    for idx in pool:
        current_text = chunks[idx]
        redundant = False

        for kept_idx in selected:
            kept_text = chunks[kept_idx]

            if detector.exact_duplicate(current_text, kept_text):
                redundant = True
                break

            if detector.near_duplicate(current_text, kept_text, threshold=threshold):
                redundant = True
                break

        if not redundant:
            selected.append(idx)

        if len(selected) >= top_k:
            break

    # Fallback: if filtering is too aggressive, fill with original ranked results
    if len(selected) < top_k:
        for idx in ordered:
            if idx not in selected:
                selected.append(idx)
            if len(selected) >= top_k:
                break

    return selected[:top_k]