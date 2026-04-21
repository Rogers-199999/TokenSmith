from src.duplicate_detector import DuplicateDetector
from src.retrieval_dedup import deduplicate_retrieved_chunk_indices


def test_exact_duplicate():
    detector = DuplicateDetector()
    assert detector.exact_duplicate(
        "A database schema is the logical design of the database.",
        "A database schema is the logical design of the database."
    )


def test_near_duplicate():
    detector = DuplicateDetector()
    a = "A database schema is the logical design of the database."
    b = "A schema is the logical design of a database."
    assert detector.near_duplicate(a, b, threshold=0.5)


def test_deduplicate_retrieved_chunk_indices():
    chunks = [
        "A database schema is the logical design of the database.",
        "A database schema is the logical design of the database.",
        "A schema is the logical design of a database.",
        "A database instance is a snapshot of the data at a given time.",
    ]
    ordered = [0, 1, 2, 3]

    filtered = deduplicate_retrieved_chunk_indices(
        chunks=chunks,
        ordered=ordered,
        top_k=3,
        threshold=0.7,
        pool_multiplier=3,
    )

    assert len(filtered) == 3
    assert 0 in filtered
    assert 3 in filtered