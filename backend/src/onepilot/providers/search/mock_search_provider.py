from __future__ import annotations

from onepilot.providers.search.base import SearchProvider

_CANNED_RESULTS: list[dict] = [
    {
        "title": "OnePilot AI - Official Documentation",
        "url": "https://docs.onepilot.example.com",
        "snippet": "Comprehensive guides for using the OnePilot AI workspace platform.",
    },
    {
        "title": "Getting Started with AI Assistants",
        "url": "https://blog.example.com/ai-assistants-guide",
        "snippet": "Learn how to integrate AI assistants into your business workflow.",
    },
    {
        "title": "Best Practices for Multi-Tenant SaaS",
        "url": "https://saas.example.com/multi-tenant-best-practices",
        "snippet": "Architecture patterns for building scalable multi-tenant applications.",
    },
    {
        "title": "CRM Integration Patterns",
        "url": "https://dev.example.com/crm-integration",
        "snippet": "How to connect your CRM with modern API-first platforms.",
    },
    {
        "title": "Email Automation Workflows",
        "url": "https://blog.example.com/email-automation",
        "snippet": "Automate email drafting and approval workflows in your team.",
    },
]


class MockSearchProvider(SearchProvider):
    """Canned-response search provider for tests and demos."""

    def search_web(self, query: str, num_results: int = 5) -> list[dict]:
        results = [
            {**r, "query": query} for r in _CANNED_RESULTS[:num_results]
        ]
        return results
