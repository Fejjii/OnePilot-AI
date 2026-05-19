"""Tests for evaluation summary API and report shapes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from onepilot.evaluation.reporting import LATEST_JSON, REPORT_DIR
from onepilot.evaluation.run_intent_eval import DEFAULT_DATASET, evaluate, load_dataset
from onepilot.evaluation.run_rag_eval import DEFAULT_DATASET as RAG_DATASET
from onepilot.evaluation.run_rag_eval import evaluate_rag, load_dataset as load_rag
from onepilot.evaluation.run_rag_eval import load_demo_index
from onepilot.evaluation.run_safety_eval import DEFAULT_DATASET as SAFETY_DATASET
from onepilot.evaluation.run_safety_eval import evaluate as evaluate_safety
from onepilot.evaluation.run_safety_eval import load_dataset as load_safety
from onepilot.services.evaluation_service import build_sample_report, get_evaluation_summary


def test_evaluation_summary_empty_when_no_report(monkeypatch, client: TestClient) -> None:
    monkeypatch.setattr(
        "onepilot.services.evaluation_service.load_latest_report",
        lambda: None,
    )
    resp = client.get("/evaluation/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is False
    assert "not generated" in (body.get("message") or "").lower()


def test_evaluation_summary_with_sample_report(monkeypatch, client: TestClient) -> None:
    sample = build_sample_report()
    monkeypatch.setattr(
        "onepilot.services.evaluation_service.load_latest_report",
        lambda: sample,
    )
    resp = client.get("/evaluation/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["metrics"]["intent_accuracy"] == 0.95
    assert body["metrics"]["failed_cases"] == 2
    assert body["hitl_approval_safety"]["sensitive_actions_require_approval"] is True


def test_intent_eval_summary_output_shape() -> None:
    report = evaluate(load_dataset(DEFAULT_DATASET))
    data = report.to_dict()
    assert "intent_accuracy" in data
    assert "routing_accuracy" in data
    assert data["total"] >= 20
    assert isinstance(data["failures"], list)


def test_rag_eval_summary_output_shape() -> None:
    report = evaluate_rag(load_rag(RAG_DATASET), load_demo_index())
    data = report.to_dict()
    assert "rag_golden_pass_rate" in data
    assert "citation_presence_rate" in data
    assert "source_hit_rate" in data
    assert "weak_evidence_correctness" in data


def test_safety_eval_summary_output_shape() -> None:
    report = evaluate_safety(load_safety(SAFETY_DATASET))
    data = report.to_dict()
    assert data["safety_guardrail_pass_rate"] >= 0.0
    assert "hitl_approval_safety" in data
    assert data["hitl_approval_safety"]["ai_can_draft_not_send_without_approval"] is True


def test_get_evaluation_summary_reads_file(tmp_path: Path, monkeypatch) -> None:
    report_path = tmp_path / "latest.json"
    sample = build_sample_report()
    report_path.write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setattr(
        "onepilot.evaluation.reporting.LATEST_JSON",
        report_path,
    )
    monkeypatch.setattr(
        "onepilot.services.evaluation_service.load_latest_report",
        lambda: json.loads(report_path.read_text(encoding="utf-8")),
    )
    summary = get_evaluation_summary()
    assert summary.available is True
    assert summary.metrics is not None
    assert summary.metrics.intent_accuracy == 0.95
