"""Tests for ingestion_service loaders."""

from __future__ import annotations

import pytest

from onepilot.core.errors import ValidationError
from onepilot.services.ingestion_service import (
    load_csv,
    load_document,
    load_markdown,
    load_text,
)


class TestLoadText:
    def test_load_plain_text(self) -> None:
        title, text = load_text(b"Hello world.\nMore content.", "note.txt")
        assert "Hello world" in text
        assert title == "Hello world."

    def test_empty_text_raises(self) -> None:
        with pytest.raises(ValidationError):
            load_text(b"", "empty.txt")


class TestLoadMarkdown:
    def test_extracts_heading_as_title(self) -> None:
        content = b"# Pricing Plans\nAll prices in USD."
        title, text = load_markdown(content, "pricing.md")
        assert title == "Pricing Plans"
        assert "All prices in USD" in text

    def test_fallback_title_when_no_heading(self) -> None:
        title, _ = load_markdown(b"No heading here, just text.", "policy.md")
        assert title.startswith("No heading here")


class TestLoadCsv:
    def test_serializes_csv_rows(self) -> None:
        csv_bytes = b"name,plan\nAcme,pro\nBeta,business"
        title, text = load_csv(csv_bytes, "customers.csv")
        assert "name" in text and "plan" in text
        assert "Acme" in text and "Beta" in text
        assert title

    def test_empty_csv_raises(self) -> None:
        with pytest.raises(ValidationError):
            load_csv(b"", "empty.csv")


class TestLoadDocumentDispatch:
    def test_dispatch_by_mime(self) -> None:
        title, text = load_document(b"# Hello\nbody.", "x.md", "text/markdown")
        assert title == "Hello"
        assert "body" in text

    def test_dispatch_by_extension(self) -> None:
        title, _ = load_document(b"# Backup\nbody.", "fallback.md", "")
        assert title == "Backup"

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(ValidationError):
            load_document(b"binary", "image.png", "image/png")


class TestOptionalLoaders:
    def test_pdf_loader_raises_clearly_when_missing(self) -> None:
        try:
            import pypdf  # noqa: F401
        except ImportError:
            from onepilot.services.ingestion_service import load_pdf

            with pytest.raises(ValidationError):
                load_pdf(b"%PDF-1.4", "missing.pdf")
        else:
            pytest.skip("pypdf is installed; cannot verify missing-dependency error")

    def test_docx_loader_raises_clearly_when_missing(self) -> None:
        try:
            import docx  # noqa: F401
        except ImportError:
            from onepilot.services.ingestion_service import load_docx

            with pytest.raises(ValidationError):
                load_docx(b"PK\x03\x04", "missing.docx")
        else:
            pytest.skip("python-docx is installed; cannot verify missing-dependency error")
