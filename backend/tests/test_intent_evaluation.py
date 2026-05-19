"""Tests for the deterministic intent evaluation harness."""

from __future__ import annotations

from pathlib import Path

from onepilot.evaluation.run_intent_eval import (
    DEFAULT_DATASET,
    evaluate,
    load_dataset,
)


def test_default_dataset_exists() -> None:
    assert DEFAULT_DATASET.exists(), "Default eval dataset is missing"
    assert DEFAULT_DATASET.is_file()


def test_load_dataset_returns_rows() -> None:
    rows = load_dataset(DEFAULT_DATASET)
    assert len(rows) >= 20
    for row in rows:
        assert "message" in row
        assert "expected_intent" in row


def test_evaluate_default_dataset_high_accuracy() -> None:
    rows = load_dataset(DEFAULT_DATASET)
    report = evaluate(rows)
    assert report.total >= 20
    assert report.accuracy >= 0.85, f"Accuracy {report.accuracy:.2%} is too low"


def test_evaluate_skips_invalid_rows(tmp_path: Path) -> None:
    bad = tmp_path / "bad.jsonl"
    bad.write_text(
        '{"message": "ok"}\n'
        '{"message": "What is our company refund policy?", "expected_intent": "knowledge_search"}\n'
        '{"message": "what", "expected_intent": "not_a_real_intent"}\n',
        encoding="utf-8",
    )
    rows = load_dataset(bad)
    report = evaluate(rows)
    assert report.total == 1
    assert report.correct == 1


def test_report_to_dict_serializes() -> None:
    rows = load_dataset(DEFAULT_DATASET)
    report = evaluate(rows)
    d = report.to_dict()
    assert "accuracy" in d
    assert "confusion" in d
    assert "per_intent_accuracy" in d
