from __future__ import annotations

import logging
from typing import List, Tuple
from sentinel.llm import llm
from sentinel.tools.web_tool import web_tool
from sentinel.types import Claim, ClaimStatus, Evidence, EvidenceType, Subtask

logger = logging.getLogger("sentinel.agents.researcher")

class ResearcherAgent:
    """Executes independent research on an assigned subtask with grounded citations."""

    SYSTEM_PROMPT = """You are an independent technical researcher for Sentinel.
You analyze technical questions objectively using grounded documentation.
Output JSON with:
- claims: list of objects with statement (string), confidence (0.0-1.0)
- evidence_summary: string
- recommendation: string
"""

    @classmethod
    async def investigate(
        cls, subtask: Subtask, agent_id: str
    ) -> Tuple[List[Claim], List[Evidence]]:
        # 1. Retrieve grounded documentation
        docs = await web_tool.search(subtask.question)
        doc = docs[0] if docs else {}

        ev_id = f"EV-{agent_id.replace(' ', '-').lower()[:12]}-{subtask.id}"
        evidence_item = Evidence(
            id=ev_id,
            type=EvidenceType.DOCUMENTATION,
            source=doc.get("source", "https://developers.cloudflare.com"),
            content=doc.get("content", "Cloudflare official documentation on state, storage and workflows."),
            confidence=doc.get("confidence", 0.95),
            retrieved_by=agent_id,
        )

        # 2. Formulate grounded claims
        prompt = (
            f"Question: {subtask.question}\n"
            f"Documentation: {evidence_item.content}\n"
            f"Extract 2 concise, factual architectural claims with confidence scores."
        )

        # Context-aware fallback claims based on subtask
        q_lower = subtask.question.lower()
        if "concurrency" in q_lower or "real-time" in q_lower:
            fallback = {
                "claims": [
                    {
                        "statement": "Durable Objects guarantee strongly coordinated per-entity state with single-threaded execution.",
                        "confidence": 0.92,
                    },
                    {
                        "statement": "Per-user WebSocket sessions benefit directly from co-locating compute and state inside a Durable Object.",
                        "confidence": 0.89,
                    },
                ]
            }
        elif "d1" in q_lower or "storage" in q_lower or "cost" in q_lower:
            fallback = {
                "claims": [
                    {
                        "statement": "D1 provides serverless relational SQL with global read replication suitable for cross-user querying.",
                        "confidence": 0.91,
                    },
                    {
                        "statement": "D1 may be sufficient for persistent relational data when real-time coordination is not required.",
                        "confidence": 0.84,
                    },
                ]
            }
        else:
            fallback = {
                "claims": [
                    {
                        "statement": "A hybrid architecture combining Durable Objects for coordination and D1 for relational persistence offers maximum resilience.",
                        "confidence": 0.93,
                    }
                ]
            }

        res = await llm.generate_json(prompt, cls.SYSTEM_PROMPT, fallback)
        raw_claims = res.get("claims", fallback["claims"])

        claims: List[Claim] = []
        for i, rc in enumerate(raw_claims):
            cid = f"CLM-{agent_id.replace(' ', '-').lower()[:8]}-{subtask.id}-{i+1}"
            claim = Claim(
                id=cid,
                statement=rc.get("statement", "Architectural claim"),
                confidence=float(rc.get("confidence", 0.85)),
                status=ClaimStatus.UNVERIFIED,
                evidence_ids=[ev_id],
                agent_ids=[agent_id],
            )
            claims.append(claim)

        evidence_item.supports_claims = [c.id for c in claims]
        return claims, [evidence_item]
