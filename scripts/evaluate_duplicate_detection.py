import json
import pickle
from pathlib import Path

from src.duplicate_detector import DuplicateDetector


def load_chunks(chunks_path):
    with open(chunks_path, "rb") as f:
        return pickle.load(f)


def load_pairs(pairs_path):
    with open(pairs_path, "r", encoding="utf-8") as f:
        return json.load(f)


def label_to_binary(label):
    if label in {"exact_duplicate", "near_duplicate"}:
        return 1
    elif label == "non_duplicate":
        return 0
    else:
        raise ValueError(f"Unknown label: {label}")


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    accuracy = (tp + tn) / len(y_true) if y_true else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_threshold(chunks, pairs, threshold):
    detector = DuplicateDetector()

    y_true = []
    y_pred = []
    details = []

    for row in pairs:
        a_id = row["chunk_a_id"]
        b_id = row["chunk_b_id"]
        gold = row["label"]

        text_a = chunks[a_id]
        text_b = chunks[b_id]

        exact = detector.exact_duplicate(text_a, text_b)
        sim = detector.jaccard_similarity(text_a, text_b)

        pred_positive = exact or (sim >= threshold)

        y_true.append(label_to_binary(gold))
        y_pred.append(1 if pred_positive else 0)

        details.append({
            "id": row["id"],
            "chunk_a_id": a_id,
            "chunk_b_id": b_id,
            "gold_label": gold,
            "similarity": sim,
            "exact_duplicate": exact,
            "pred_positive": pred_positive,
            "notes": row.get("notes", "")
        })

    metrics = compute_metrics(y_true, y_pred)
    return metrics, details


def main():
    chunks_path = "index/sections/textbook_index_chunks.pkl"
    pairs_path = "evaluation/labeled_pairs.json"
    output_path = "evaluation/detection_results.json"

    thresholds = [0.5, 0.3, 0.2, 0.1]

    chunks = load_chunks(chunks_path)
    pairs = load_pairs(pairs_path)

    all_results = {}

    for threshold in thresholds:
        metrics, details = evaluate_threshold(chunks, pairs, threshold)
        all_results[str(threshold)] = {
            "metrics": metrics,
            "details": details
        }

        print(f"\n=== Threshold {threshold} ===")
        for k, v in metrics.items():
            print(f"{k}: {v}")

    Path("evaluation").mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved results to {output_path}")


if __name__ == "__main__":
    main()