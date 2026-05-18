from __future__ import annotations

import hashlib
import math
import re
from typing import Final

from onepilot.providers.embeddings.base import EmbeddingsProvider

_DIMENSION: Final[int] = 384
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_STOPWORDS: Final[frozenset[str]] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "do",
        "does",
        "for",
        "from",
        "have",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "they",
        "this",
        "to",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
    }
)


class FallbackEmbeddingsProvider(EmbeddingsProvider):
    """Deterministic bag-of-tokens hashing embedding for tests and local demo.

    The embedding is the L2-normalized vector produced by hashing each non-stopword
    token to a position in a fixed-dimension space. This is intentionally simple
    but preserves semantic overlap: queries and passages sharing tokens will have
    cosine similarity above zero, while unrelated text will be near zero.

    It is not a substitute for a real embedding model in production, only a
    deterministic fallback for offline tests and local demos.
    """

    @property
    def dimension(self) -> int:
        return _DIMENSION

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str, model: str | None = None) -> list[float]:
        return self._embed_one(text)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [
            tok.lower()
            for tok in _TOKEN_RE.findall(text)
            if tok.lower() not in _STOPWORDS and len(tok) > 1
        ]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vector = [0.0] * _DIMENSION
        tokens = FallbackEmbeddingsProvider._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            primary = int.from_bytes(digest[:4], "little") % _DIMENSION
            secondary = int.from_bytes(digest[4:], "little") % _DIMENSION
            sign = 1.0 if (digest[0] & 1) == 0 else -1.0
            vector[primary] += sign
            vector[secondary] += sign * 0.5

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
