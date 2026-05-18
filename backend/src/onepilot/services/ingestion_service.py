"""Document ingestion helpers.

Each loader returns a tuple of ``(title, plain_text)``. The chunking service then
slices the plain text into searchable chunks. PDF and DOCX support is
"best-effort" — if the optional dependency is missing, callers receive a
:class:`ValidationError` rather than a crash.
"""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Callable

from onepilot.core.errors import ValidationError

SUPPORTED_TEXT_TYPES: set[str] = {
    "text/plain",
    "text/markdown",
    "text/csv",
}
SUPPORTED_BINARY_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValidationError("Unable to decode text content")


def _extract_title(filename: str, text: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
        if line:
            return line[:120]
    base = os.path.basename(filename)
    return os.path.splitext(base)[0].replace("_", " ").title()


def load_text(content: bytes, filename: str) -> tuple[str, str]:
    text = _decode_text(content).strip()
    if not text:
        raise ValidationError("Document is empty")
    return _extract_title(filename, text), text


def load_markdown(content: bytes, filename: str) -> tuple[str, str]:
    return load_text(content, filename)


def load_csv(content: bytes, filename: str) -> tuple[str, str]:
    text = _decode_text(content)
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValidationError("CSV is empty")

    header = rows[0]
    body_lines: list[str] = [", ".join(header)]
    for row in rows[1:]:
        pairs = [
            f"{header[idx]}: {value}"
            for idx, value in enumerate(row)
            if idx < len(header)
        ]
        body_lines.append("; ".join(pairs))
    plain_text = "\n".join(body_lines)
    return _extract_title(filename, plain_text), plain_text


def load_pdf(content: bytes, filename: str) -> tuple[str, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValidationError(
            "PDF support requires the optional 'pypdf' dependency"
        ) from exc

    reader = PdfReader(io.BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    full = "\n\n".join(pages).strip()
    if not full:
        raise ValidationError("PDF contained no extractable text")
    return _extract_title(filename, full), full


def load_docx(content: bytes, filename: str) -> tuple[str, str]:
    try:
        import docx
    except ImportError as exc:
        raise ValidationError(
            "DOCX support requires the optional 'python-docx' dependency"
        ) from exc

    document = docx.Document(io.BytesIO(content))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    full = "\n\n".join(paragraphs).strip()
    if not full:
        raise ValidationError("DOCX contained no extractable text")
    return _extract_title(filename, full), full


_LOADER_BY_MIME: dict[str, Callable[[bytes, str], tuple[str, str]]] = {
    "text/plain": load_text,
    "text/markdown": load_markdown,
    "text/csv": load_csv,
    "application/pdf": load_pdf,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": load_docx,
}

_LOADER_BY_EXT: dict[str, Callable[[bytes, str], tuple[str, str]]] = {
    ".txt": load_text,
    ".md": load_markdown,
    ".csv": load_csv,
    ".pdf": load_pdf,
    ".docx": load_docx,
}


def load_document(content: bytes, filename: str, content_type: str) -> tuple[str, str]:
    """Dispatch to the appropriate loader based on MIME type / extension."""
    loader = _LOADER_BY_MIME.get(content_type)
    if loader is None:
        _, ext = os.path.splitext(filename)
        loader = _LOADER_BY_EXT.get(ext.lower())
    if loader is None:
        raise ValidationError(f"Unsupported document type: {content_type or filename}")
    return loader(content, filename)


__all__ = [
    "SUPPORTED_TEXT_TYPES",
    "SUPPORTED_BINARY_TYPES",
    "load_csv",
    "load_docx",
    "load_document",
    "load_markdown",
    "load_pdf",
    "load_text",
]
