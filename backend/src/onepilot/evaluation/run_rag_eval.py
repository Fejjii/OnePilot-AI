"""RAG retrieval evaluation harness.

Tests RAG retrieval quality against golden query-document pairs.
Measures precision@k and recall@k for a set of test queries.

Usage:

    python -m onepilot.evaluation.run_rag_eval
    python -m onepilot.evaluation.run_rag_eval --json-output reports/evaluation/rag_eval.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from onepilot.core.config import get_settings
from onepilot.core.logging import get_logger
from onepilot.providers import get_embeddings_provider, get_vector_provider

logger = get_logger(__name__)

DEFAULT_OUTPUT_DIR = Path("reports/evaluation")


# Golden test queries with expected document matches
GOLDEN_QUERIES = [
    {
        "query": "What is the refund policy?",
        "expected_documents": ["refund_policy.md", "terms_of_service.md"],
        "category": "policy",
    },
    {
        "query": "How do I upgrade my plan?",
        "expected_documents": ["pricing_plans.md", "billing_faq.md"],
        "category": "billing",
    },
    {
        "query": "What security measures are in place?",
        "expected_documents": ["security_overview.md", "data_privacy.md"],
        "category": "security",
    },
    {
        "query": "Can I integrate with Slack?",
        "expected_documents": ["integrations.md", "slack_guide.md"],
        "category": "integrations",
    },
    {
        "query": "How do I export my data?",
        "expected_documents": ["data_export.md", "api_docs.md"],
        "category": "data",
    },
]


@dataclass(slots=True)
class RAGEvalReport:
    total_queries: int = 0
    total_hits: int = 0
    precision_at_3: float = 0.0
    recall_at_3: float = 0.0
    avg_relevance_score: float = 0.0
    queries_with_results: int = 0
    queries_without_results: int = 0
    category_performance: dict[str, dict] = field(default_factory=dict)
    query_results: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "test_name": "rag_retrieval",
            "timestamp": self.timestamp,
            "total_queries": self.total_queries,
            "total_hits": self.total_hits,
            "precision_at_3": round(self.precision_at_3, 4),
            "recall_at_3": round(self.recall_at_3, 4),
            "avg_relevance_score": round(self.avg_relevance_score, 4),
            "queries_with_results": self.queries_with_results,
            "queries_without_results": self.queries_without_results,
            "category_performance": self.category_performance,
            "query_results": self.query_results,
        }

    def to_markdown(self) -> str:
        """Generate a Markdown summary report."""
        lines = [
            "# RAG Retrieval Evaluation Report",
            "",
            f"**Generated:** {self.timestamp}",
            "",
            "## Summary",
            "",
            f"- **Total queries:** {self.total_queries}",
            f"- **Queries with results:** {self.queries_with_results}",
            f"- **Queries without results:** {self.queries_without_results}",
            f"- **Precision@3:** {self.precision_at_3:.2%}",
            f"- **Recall@3:** {self.recall_at_3:.2%}",
            f"- **Average relevance score:** {self.avg_relevance_score:.3f}",
            "",
            "## Category Performance",
            "",
            "| Category | Queries | Hits | Precision@3 |",
            "|----------|---------|------|-------------|",
        ]

        for category, stats in sorted(self.category_performance.items()):
            lines.append(
                f"| {category} | {stats['count']} | {stats['hits']} | {stats['precision']:.2%} |"
            )

        lines.extend([
            "",
            "## Query Results",
            "",
        ])

        for result in self.query_results:
            status = "✓" if result["hit"] else "✗"
            lines.append(f"### {status} {result['query']}")
            lines.append(f"- **Expected:** {', '.join(result['expected_documents'])}")
            lines.append(f"- **Retrieved:** {result['retrieved_count']} documents")
            lines.append(f"- **Hit:** {'Yes' if result['hit'] else 'No'}")
            if result["retrieved_titles"]:
                lines.append(f"- **Top 3:** {', '.join(result['retrieved_titles'][:3])}")
            lines.append("")

        return "\n".join(lines)


def evaluate_rag(queries: list[dict]) -> RAGEvalReport:
    """Run RAG evaluation on golden queries.
    
    Note: This is a placeholder implementation that demonstrates the structure.
    In a real evaluation, you would:
    1. Query the vector store with each query
    2. Check if expected documents are in top-k results
    3. Calculate precision/recall metrics
    """
    settings = get_settings()
    report = RAGEvalReport(total_queries=len(queries))

    # Placeholder: In real implementation, query vector store
    logger.info("RAG evaluation: This is a placeholder implementation")
    logger.info("To run real RAG evaluation:")
    logger.info("1. Ensure knowledge base is seeded with test documents")
    logger.info("2. Implement vector search against the test queries")
    logger.info("3. Compare retrieved documents against expected_documents")

    # Simulate results for demonstration
    for query_data in queries:
        query = query_data["query"]
        expected = query_data["expected_documents"]
        category = query_data.get("category", "other")

        # Placeholder result
        result = {
            "query": query,
            "expected_documents": expected,
            "retrieved_count": 0,
            "retrieved_titles": [],
            "hit": False,
            "relevance_score": 0.0,
            "category": category,
        }

        # Track category performance
        if category not in report.category_performance:
            report.category_performance[category] = {
                "count": 0,
                "hits": 0,
                "precision": 0.0,
            }

        report.category_performance[category]["count"] += 1
        report.query_results.append(result)

    # Calculate aggregate metrics
    if report.total_queries > 0:
        report.precision_at_3 = report.total_hits / report.total_queries
        report.recall_at_3 = report.precision_at_3  # Simplified for placeholder

    for category, stats in report.category_performance.items():
        if stats["count"] > 0:
            stats["precision"] = stats["hits"] / stats["count"]

    logger.warning("RAG evaluation completed with placeholder data")
    logger.warning("Implement real vector search for production-ready evaluation")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RAG retrieval evaluation")
    parser.add_argument("--queries", type=Path, help="Custom queries JSONL file")
    parser.add_argument("--json-output", type=Path, help="Write JSON report to file")
    parser.add_argument("--markdown-output", type=Path, help="Write Markdown report to file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true", help="Print JSON output to stdout")
    args = parser.parse_args(argv)

    # Load queries
    if args.queries and args.queries.exists():
        queries = []
        for line in args.queries.read_text().splitlines():
            if line.strip():
                queries.append(json.loads(line))
    else:
        queries = GOLDEN_QUERIES

    report = evaluate_rag(queries)

    # Write JSON report if requested
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"JSON report written to: {args.json_output}")

    # Write Markdown report if requested
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(report.to_markdown(), encoding="utf-8")
        print(f"Markdown report written to: {args.markdown_output}")

    # Write to output_dir/latest.json and output_dir/latest.md by default
    if not args.json_output and not args.markdown_output:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "rag_eval_latest.json").write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        (args.output_dir / "rag_eval_latest.md").write_text(report.to_markdown(), encoding="utf-8")
        print(f"Reports written to: {args.output_dir}/rag_eval_latest.{{json,md}}")

    # Print to stdout
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
        return 0

    print(f"Total queries: {report.total_queries}")
    print(f"Precision@3:   {report.precision_at_3:.2%}")
    print(f"Recall@3:      {report.recall_at_3:.2%}")
    print(f"Avg relevance: {report.avg_relevance_score:.3f}")
    print()
    print("Category performance:")
    for category, stats in sorted(report.category_performance.items()):
        print(f"  {category:<15} {stats['hits']}/{stats['count']} ({stats['precision']:.0%})")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    sys.exit(main())
