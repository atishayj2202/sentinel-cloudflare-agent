from __future__ import annotations

import logging
from typing import List
from sentinel.llm import llm
from sentinel.types import Subtask

logger = logging.getLogger("sentinel.agents.planner")

class PlannerAgent:
    """Decomposes the mission objective into independent investigation subtasks."""

    SYSTEM_PROMPT = """You are the Sentinel Chief Architecture Planner.
Your role is to decompose complex systems and architecture questions into independent, parallel investigation vectors.
Ensure you investigate:
1. Concurrency and real-time state coordination
2. Persistence, scale, storage constraints, and pricing
3. Workload fit and operational simplicity

Output JSON with keys:
- objective: string
- subtasks: array of objects with id, type, question, assigned_agent
"""

    @classmethod
    async def plan(cls, user_request: str) -> List[Subtask]:
        prompt = f"Decompose this mission request into independent research subtasks:\nRequest: \"{user_request}\""

        fallback = {
            "objective": f"Evaluate optimal architecture for: {user_request}",
            "subtasks": [
                {
                    "id": "SUB-01",
                    "type": "research",
                    "question": "What are the real-time state coordination and concurrency guarantees required?",
                    "assigned_agent": "Architecture Researcher",
                },
                {
                    "id": "SUB-02",
                    "type": "research",
                    "question": "How do D1 and Durable Objects compare on relational querying, storage persistence, and scale?",
                    "assigned_agent": "Scale & Cost Researcher",
                },
                {
                    "id": "SUB-03",
                    "type": "research",
                    "question": "What is the optimal architecture and developer workflow for the given workload constraints?",
                    "assigned_agent": "Workload Fit Analyst",
                },
            ],
        }

        res = await llm.generate_json(prompt, cls.SYSTEM_PROMPT, fallback)
        subtask_dicts = res.get("subtasks", fallback["subtasks"])
        subtasks: List[Subtask] = []
        for s in subtask_dicts:
            subtasks.append(
                Subtask(
                    id=s.get("id", f"SUB-{len(subtasks)+1:02d}"),
                    type=s.get("type", "research"),
                    question=s.get("question", "General investigation"),
                    assigned_agent=s.get("assigned_agent", "General Researcher"),
                )
            )
        return subtasks
