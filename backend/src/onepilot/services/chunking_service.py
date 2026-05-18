"""Pure-function chunking helpers used by document ingestion.

Chunking is intentionally simple and deterministic so it is easy to test:
- We split the raw text into paragraphs.
- We preserve the most recent Markdown heading (`#`, `##`, `###`) as the section.
- We pack paragraphs into chunks of roughly `chunk_size` characters with an overlap
  of `overlap` characters between adjacent chunks.

A token count is approximated as ``len(content) / 4`` which is close enough for
quota/cost estimation in the demo environment. A proper tokenizer would be used
in production but is unnecessary for the test suite.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

DEFAULT_CHUNK_SIZE: int = 800
DEFAULT_OVERLAP: int = 100

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(slots=True)
class Chunk:
    ordinal: int
    content: str
    section: str | None
    token_count: int

    def to_dict(self) -> dict:
        return {
            "ordinal": self.ordinal,
            "content": self.content,
            "section": self.section,
            "token_count": self.token_count,
        }


def _approx_tokens(content: str) -> int:
    return max(1, len(content) // 4)


def _split_paragraphs(text: str) -> Iterable[tuple[str | None, str]]:
    """Yield (current_section, paragraph) pairs preserving the most recent heading."""
    section: str | None = None
    buffer: list[str] = []

    def flush() -> Iterable[tuple[str | None, str]]:
        if buffer:
            paragraph = "\n".join(buffer).strip()
            if paragraph:
                yield section, paragraph
        buffer.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            yield from flush()
            section = heading_match.group(2).strip()
            continue
        if not line.strip():
            yield from flush()
            continue
        buffer.append(line)
    yield from flush()


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split text into deterministic chunks suitable for embedding.

    `text` is parsed in paragraph order; each chunk carries the most recent
    Markdown heading as `section`. A small overlap between adjacent chunks
    keeps context bleeding across paragraph boundaries.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")

    chunks: list[Chunk] = []
    ordinal = 0
    current_section: str | None = None
    current_text = ""

    def emit() -> None:
        nonlocal ordinal, current_text
        if not current_text.strip():
            current_text = ""
            return
        content = current_text.strip()
        chunks.append(
            Chunk(
                ordinal=ordinal,
                content=content,
                section=current_section,
                token_count=_approx_tokens(content),
            )
        )
        ordinal += 1
        if overlap > 0:
            tail = content[-overlap:]
            current_text = tail + "\n"
        else:
            current_text = ""

    for section, paragraph in _split_paragraphs(text):
        if section != current_section and current_text.strip():
            emit()
        current_section = section

        if len(current_text) + len(paragraph) + 1 > chunk_size:
            emit()

        if len(paragraph) > chunk_size:
            for window in _hard_split(paragraph, chunk_size, overlap):
                if current_text.strip():
                    emit()
                current_text = window + "\n"
                if len(current_text) >= chunk_size:
                    emit()
        else:
            if current_text:
                current_text += "\n"
            current_text += paragraph

    if current_text.strip():
        emit()

    return chunks


def _hard_split(paragraph: str, chunk_size: int, overlap: int) -> Iterable[str]:
    """Split a paragraph that is larger than `chunk_size` into overlapping windows."""
    step = max(1, chunk_size - overlap)
    for start in range(0, len(paragraph), step):
        end = min(len(paragraph), start + chunk_size)
        yield paragraph[start:end]
        if end == len(paragraph):
            break


__all__ = ["Chunk", "chunk_text", "DEFAULT_CHUNK_SIZE", "DEFAULT_OVERLAP"]
