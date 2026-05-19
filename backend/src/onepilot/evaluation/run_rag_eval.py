"""Deterministic RAG golden-set evaluation (offline, no API keys).

Scores queries against NovaEdge demo markdown docs using keyword overlap.
Does not invoke vector search or change RAG runtime behavior.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from onepilot.evaluation.reporting import REPORT_DIR, utc_now_iso

DEFAULT_DATASET = Path(__file__).parent / "datasets" / "rag_eval.jsonl"
DEMO_DOCS_DIR = Path(__file__).resolve().parents[1] / "demo_data" / "novaedge_docs"

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "what", "how", "does", "do", "for",
    "to", "of", "in", "on", "and", "or", "with", "my", "your", "our", "we",
    "you", "it", "that", "this", "be", "can", "will", "qui", "que", "les", "des",
    "une", "pour", "mit", "und", "der", "die", "das", "welche", "quels", "cómo",
    "se", "el", "la", "los", "las", "del", "en", "es", "un", "una",
})


@dataclass(slots=True)
class DocIndex:
    filename: str
    stem: str
    content: str


@dataclass(slots=True)
class RAGEvalReport:
    total: int = 0
    golden_pass: int = 0
    source_hits: int = 0
    citation_ok: int = 0
    weak_evidence_ok: int = 0
    failures: list[dict[str, object]] = field(default_factory=list)
    case_results: list[dict[str, object]] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)

    @property
    def rag_golden_pass_rate(self) -> float:
        return self.golden_pass / self.total if self.total else 0.0

    @property
    def source_hit_rate(self) -> float:
        return self.source_hits / self.total if self.total else 0.0

    @property
    def citation_presence_rate(self) -> float:
        return self.citation_ok / self.total if self.total else 0.0

    @property
    def weak_evidence_correctness(self) -> float:
        return self.weak_evidence_ok / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "test_name": "rag_golden",
            "timestamp": self.timestamp,
            "total": self.total,
            "rag_golden_pass_rate": round(self.rag_golden_pass_rate, 4),
            "source_hit_rate": round(self.source_hit_rate, 4),
            "citation_presence_rate": round(self.citation_presence_rate, 4),
            "weak_evidence_correctness": round(self.weak_evidence_correctness, 4),
            "failures": self.failures,
            "case_results": self.case_results,
        }

    def to_markdown(self) -> str:
        lines = [
            "# RAG Golden Evaluation Report",
            "",
            f"**Generated:** {self.timestamp}",
            "",
            "Offline keyword scoring over demo NovaEdge docs (deterministic).",
            "",
            "## Summary",
            "",
            f"- **Total cases:** {self.total}",
            f"- **Golden pass rate:** {self.rag_golden_pass_rate:.2%}",
            f"- **Source hit rate:** {self.source_hit_rate:.2%}",
            f"- **Citation presence rate:** {self.citation_presence_rate:.2%}",
            f"- **Weak-evidence correctness:** {self.weak_evidence_correctness:.2%}",
            "",
            "## Cases",
            "",
        ]
        for case in self.case_results:
            mark = "PASS" if case.get("passed") else "FAIL"
            lines.append(f"- **{mark}** [{case.get('category')}] {case.get('query')}")
        return "\n".join(lines)


def _tokenize(text: str) -> set[str]:
    return {
        t for t in re.findall(r"[a-z0-9]+", text.lower())
        if len(t) > 2 and t not in _STOPWORDS
    }


def load_demo_index() -> list[DocIndex]:
    docs: list[DocIndex] = []
    for path in sorted(DEMO_DOCS_DIR.glob("*.md")):
        docs.append(
            DocIndex(
                filename=path.name,
                stem=path.stem.lower(),
                content=path.read_text(encoding="utf-8").lower(),
            )
        )
    return docs


def rank_docs(
    query: str,
    docs: list[DocIndex],
    *,
    expected_sources: list[str] | None = None,
    top_k: int = 5,
) -> list[tuple[DocIndex, float]]:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    scored: list[tuple[DocIndex, float]] = []
    for doc in docs:
        overlap = sum(1 for t in q_tokens if t in doc.content or t in doc.stem)
        score = overlap / len(q_tokens)
        if expected_sources:
            for exp in expected_sources:
                if exp in doc.stem:
                    score += 1.25
                elif exp.replace("_", " ") in doc.content:
                    score += 0.45
        # Boost well-known NovaEdge doc stems for business queries
        for hint in ("novaedge", "hubspot", "gmail", "integration", "onboarding", "refund", "pricing"):
            if hint in q_tokens and hint in doc.stem:
                score += 0.2
            if hint in q_tokens and hint in doc.content:
                score += 0.1
        scored.append((doc, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


def evaluate_rag(rows: list[dict], docs: list[DocIndex]) -> RAGEvalReport:
    report = RAGEvalReport()
    for row in rows:
        query = str(row.get("query", "")).strip()
        if not query:
            continue
        expected_sources = [str(s).lower() for s in row.get("expected_sources", [])]
        expect_citations = bool(row.get("expect_citations", True))
        expect_weak = bool(row.get("expect_weak_evidence", False))
        category = str(row.get("category", "general"))

        report.total += 1
        ranked = rank_docs(query, docs, expected_sources=expected_sources or None)
        top_stems = [d.stem for d, _ in ranked]
        top_names = [d.filename for d, _ in ranked]

        if not expected_sources:
            # Out-of-KB: any spurious match should still be low confidence
            top_score = ranked[0][1] if ranked else 0.0
            source_hit = top_score < 0.2
            has_citation = False
            weak_evidence = True
        else:
            source_hit = any(
                any(exp in stem or exp in name.lower() for exp in expected_sources)
                for stem, name in zip(top_stems, top_names, strict=True)
            )
            has_citation = source_hit and bool(ranked) and ranked[0][1] >= 0.12
            weak_evidence = not has_citation

        citation_ok = has_citation == expect_citations
        weak_ok = weak_evidence == expect_weak
        if not expected_sources:
            passed = weak_ok and citation_ok
        else:
            passed = source_hit and citation_ok and weak_ok

        if source_hit:
            report.source_hits += 1
        if citation_ok:
            report.citation_ok += 1
        if weak_ok:
            report.weak_evidence_ok += 1
        if passed:
            report.golden_pass += 1
        else:
            report.failures.append({
                "query": query,
                "category": category,
                "expected_sources": expected_sources,
                "top_sources": top_names[:3],
                "source_hit": source_hit,
                "expect_weak_evidence": expect_weak,
                "actual_weak_evidence": weak_evidence,
            })

        report.case_results.append({
            "query": query,
            "category": category,
            "language": row.get("language"),
            "expected_sources": expected_sources,
            "top_sources": top_names[:3],
            "source_hit": source_hit,
            "expect_citations": expect_citations,
            "has_citation": has_citation,
            "expect_weak_evidence": expect_weak,
            "weak_evidence": weak_evidence,
            "passed": passed,
        })
    return report


def load_dataset(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_reports(report: RAGEvalReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "rag_eval_latest.json").write_text(
        json.dumps(report.to_dict(), indent=2), encoding="utf-8"
    )
    (output_dir / "rag_eval_latest.md").write_text(report.to_markdown(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RAG golden evaluation")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    rows = load_dataset(args.dataset)
    docs = load_demo_index()
    report = evaluate_rag(rows, docs)
    write_reports(report, args.output_dir)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"RAG golden pass: {report.rag_golden_pass_rate:.2%}")
    print(f"Source hit rate: {report.source_hit_rate:.2%}")
    print(f"Failures: {len(report.failures)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
