from __future__ import annotations

import re
from typing import Any, Dict, List

class CloudflareDocsTool:
    """Knowledge retriever grounded on Cloudflare documentation and benchmarks."""

    KNOWLEDGE_BASE: List[Dict[str, Any]] = [
        {
            "topic": "Durable Objects",
            "keywords": ["durable objects", "do", "coordination", "real-time", "per-user", "websocket", "state"],
            "title": "Cloudflare Durable Objects Architecture Guide",
            "content": (
                "Durable Objects provide strongly consistent, single-threaded per-entity coordination with local SQLite storage. "
                "Ideal for real-time collaboration, WebSocket state synchronization, and per-user locking. "
                "Guarantees that a single point-of-coordination exists globally for a given ID."
            ),
            "confidence": 0.96,
            "source": "https://developers.cloudflare.com/durable-objects/",
        },
        {
            "topic": "Cloudflare D1",
            "keywords": ["d1", "sqlite", "relational", "sql", "queries", "persistence", "tables"],
            "title": "Cloudflare D1 Serverless SQL Database",
            "content": (
                "Cloudflare D1 is a serverless relational SQL database built on SQLite with read replication across Cloudflare's network. "
                "Ideal for relational application data, analytical queries, user accounts, and structured catalog persistence with eventual read replication."
            ),
            "confidence": 0.94,
            "source": "https://developers.cloudflare.com/d1/",
        },
        {
            "topic": "Cloudflare Workflows",
            "keywords": ["workflows", "workflow", "durable", "retry", "human-in-the-loop", "orchestration", "multi-step"],
            "title": "Cloudflare Workflows Documentation",
            "content": (
                "Cloudflare Workflows offer durable, step-based execution guarantees with automatic retries, step persistence, "
                "and sleep/wait-for-event primitives. Workflows coordinate long-running background tasks and human approvals."
            ),
            "confidence": 0.97,
            "source": "https://developers.cloudflare.com/workflows/",
        },
        {
            "topic": "Cloudflare Workers AI",
            "keywords": ["workers ai", "llama", "llm", "inference", "gpu"],
            "title": "Cloudflare Workers AI Platform",
            "content": (
                "Workers AI runs machine learning models on Cloudflare's global GPU network with low latency and pay-per-token pricing. "
                "Supports Llama 3.3 70B Instruct, Mistral, and multimodal embedding models."
            ),
            "confidence": 0.95,
            "source": "https://developers.cloudflare.com/workers-ai/",
        },
    ]

    async def search(self, query: str) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        results: List[Dict[str, Any]] = []

        for doc in self.KNOWLEDGE_BASE:
            matches = sum(1 for kw in doc["keywords"] if re.search(r"\b" + re.escape(kw) + r"\b", query_lower))
            if matches > 0:
                results.append({
                    "title": doc["title"],
                    "content": doc["content"],
                    "source": doc["source"],
                    "confidence": doc["confidence"],
                    "relevance": matches,
                })

        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        return results if results else [self.KNOWLEDGE_BASE[0]]

web_tool = CloudflareDocsTool()
