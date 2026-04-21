import re
from typing import Set


class DuplicateDetector:
    def normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def tokenize(self, text: str) -> Set[str]:
        normalized = self.normalize(text)
        return set(normalized.split())

    def exact_duplicate(self, a: str, b: str) -> bool:
        return self.normalize(a) == self.normalize(b)

    def jaccard_similarity(self, a: str, b: str) -> float:
        a_tokens = self.tokenize(a)
        b_tokens = self.tokenize(b)

        if not a_tokens and not b_tokens:
            return 1.0
        if not a_tokens or not b_tokens:
            return 0.0

        intersection = len(a_tokens & b_tokens)
        union = len(a_tokens | b_tokens)
        return intersection / union

    def near_duplicate(self, a: str, b: str, threshold: float = 0.8) -> bool:
        return self.jaccard_similarity(a, b) >= threshold