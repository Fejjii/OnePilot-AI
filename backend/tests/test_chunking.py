"""Tests for chunking_service."""

from __future__ import annotations

import pytest

from onepilot.services.chunking_service import (
    DEFAULT_CHUNK_SIZE,
    Chunk,
    chunk_text,
)

_SAMPLE_MD = """# NovaEdge — Test Document

## Section A
This is the first paragraph in section A.

Another paragraph in section A with a bit more text so that we exercise chunking
behaviour with overlap. We want to ensure chunks carry the right section label.

## Section B
This paragraph starts section B and must be tagged accordingly. Section transitions
should produce a new chunk boundary.

A second paragraph in section B. Lorem ipsum dolor sit amet, consectetur
adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna
aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
"""


class TestChunkText:
    def test_returns_chunks_with_sections(self) -> None:
        chunks = chunk_text(_SAMPLE_MD)
        assert len(chunks) >= 2
        sections = {c.section for c in chunks if c.section}
        assert "Section A" in sections
        assert "Section B" in sections

    def test_chunks_have_ordinal_starting_at_zero(self) -> None:
        chunks = chunk_text(_SAMPLE_MD)
        assert chunks[0].ordinal == 0
        ordinals = [c.ordinal for c in chunks]
        assert ordinals == sorted(ordinals)

    def test_chunks_respect_size_bound(self) -> None:
        text = "Paragraph " + ("lorem ipsum " * 500)
        chunks = chunk_text(text, chunk_size=400, overlap=50)
        assert all(len(c.content) <= 500 for c in chunks)
        assert len(chunks) > 1

    def test_section_transition_forces_new_chunk(self) -> None:
        text = "## First\nAlpha paragraph here.\n\n## Second\nBeta paragraph here."
        chunks = chunk_text(text)
        seen_first = any(c.section == "First" for c in chunks)
        seen_second = any(c.section == "Second" for c in chunks)
        assert seen_first
        assert seen_second

    def test_invalid_overlap_raises(self) -> None:
        with pytest.raises(ValueError):
            chunk_text("hello", chunk_size=100, overlap=100)
        with pytest.raises(ValueError):
            chunk_text("hello", chunk_size=0, overlap=0)

    def test_token_count_is_positive(self) -> None:
        chunks = chunk_text(_SAMPLE_MD)
        assert all(c.token_count > 0 for c in chunks)

    def test_empty_input_returns_no_chunks(self) -> None:
        assert chunk_text("") == []
        assert chunk_text("\n\n\n") == []

    def test_chunk_dict_round_trip(self) -> None:
        chunk = Chunk(ordinal=0, content="hello world", section="Intro", token_count=2)
        as_dict = chunk.to_dict()
        assert as_dict["ordinal"] == 0
        assert as_dict["section"] == "Intro"

    def test_default_chunk_size_constant_is_reasonable(self) -> None:
        assert 200 <= DEFAULT_CHUNK_SIZE <= 4000
