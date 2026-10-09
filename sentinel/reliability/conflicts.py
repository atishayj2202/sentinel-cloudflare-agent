from __future__ import annotations

import re
from typing import List, Tuple
from sentinel.types import Claim, Conflict, ConflictSeverity, ConflictStatus

class ConflictDetector:
    """Discovers claim contradictions and identifies diverging assumptions."""

    OPPOSING_PATTERNS: List[Tuple[str, str, str]] = [
        (
            r"\b(durable objects?|do)\b",
            r"\b(d1|relational)\b",
            "Disagreement between strongly coordinated per-entity state vs relational SQL storage",
        ),
        (
            r"\b(strongly coordinated|real-time|coordination)\b",
            r"\b(eventual consistency|relational queries|analytical)\b",
            "Mismatched workload assumption regarding consistency requirements",
        ),
        (
            r"\b(high latency|unsuitable)\b",
            r"\b(low latency|recommended|optimal)\b",
            "Direct contradiction on performance characteristics",
        ),
        (
            r"\b(cost prohibitive|expensive)\b",
            r"\b(cost effective|cheaper|low cost)\b",
            "Discrepancy in cost projection and pricing model",
        ),
    ]

    @classmethod
    def detect_conflicts(cls, claims: List[Claim]) -> List[Conflict]:
        conflicts: List[Conflict] = []
        conflict_counter = 1

        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                # Agents must be different or claims must be independent
                text1 = c1.statement.lower()
                text2 = c2.statement.lower()

                for pat1, pat2, premise in cls.OPPOSING_PATTERNS:
                    if (re.search(pat1, text1) and re.search(pat2, text2)) or (
                        re.search(pat2, text1) and re.search(pat1, text2)
                    ):
                        # Ensure not duplicate
                        existing = any(
                            set(c.claim_ids) == {c1.id, c2.id} for c in conflicts
                        )
                        if not existing:
                            conflicts.append(
                                Conflict(
                                    id=f"CONF-{conflict_counter:03d}",
                                    claim_ids=[c1.id, c2.id],
                                    agent_ids=list(set(c1.agent_ids + c2.agent_ids)),
                                    reason=f"Opposing claims: '{c1.statement[:60]}...' vs '{c2.statement[:60]}...'",
                                    diverging_assumption=premise,
                                    severity=ConflictSeverity.HIGH,
                                    resolution_status=ConflictStatus.OPEN,
                                )
                            )
                            conflict_counter += 1

        return conflicts
