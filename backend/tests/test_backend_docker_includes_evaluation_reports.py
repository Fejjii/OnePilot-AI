from __future__ import annotations

from pathlib import Path


def test_backend_dockerfile_copies_evaluation_reports() -> None:
    dockerfile_path = Path(__file__).resolve().parents[1] / "Dockerfile"
    content = dockerfile_path.read_text(encoding="utf-8")

    # Production backend container serves /evaluation/summary by reading
    # /app/reports/evaluation/latest.json (see onepilot.evaluation.reporting).
    assert "COPY reports/ ./reports/" in content

