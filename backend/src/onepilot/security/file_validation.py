from __future__ import annotations

import os
from dataclasses import dataclass, field

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".txt", ".md", ".csv"}
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/csv",
}
MAX_FILE_SIZE_MB: int = 50


@dataclass
class FileValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


def validate_file(
    filename: str,
    content_type: str,
    size_bytes: int,
) -> FileValidationResult:
    """Validate a file upload by extension, MIME type, and size."""
    errors: list[str] = []

    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        errors.append(
            f"Extension '{ext}' is not allowed. "
            f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if content_type not in ALLOWED_MIME_TYPES:
        errors.append(
            f"MIME type '{content_type}' is not allowed. "
            f"Accepted: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        errors.append(
            f"File size {size_bytes / (1024 * 1024):.1f} MB exceeds "
            f"the {MAX_FILE_SIZE_MB} MB limit"
        )

    return FileValidationResult(valid=len(errors) == 0, errors=errors)
