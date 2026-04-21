import pickle
import json
from pathlib import Path

def main():
    chunks_path = "index/sections/textbook_index_chunks.pkl"
    meta_path = "index/sections/textbook_index_meta.pkl"
    output_path = "evaluation/chunk_previews.json"

    with open(chunks_path, "rb") as f:
        chunks = pickle.load(f)

    with open(meta_path, "rb") as f:
        meta = pickle.load(f)

    rows = []
    for i, chunk in enumerate(chunks):
        row = {
            "chunk_id": i,
            "section": meta[i].get("section", ""),
            "section_path": meta[i].get("section_path", ""),
            "page_numbers": meta[i].get("page_numbers", []),
            "preview": chunk[:300].replace("\n", " "),
        }
        rows.append(row)

    Path("evaluation").mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"Saved chunk previews to {output_path}")

if __name__ == "__main__":
    main()