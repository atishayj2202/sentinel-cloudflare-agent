from __future__ import annotations

import logging
from typing import Dict, List, Tuple
from sentinel.reliability.conflicts import ConflictDetector
from sentinel.reliability.evidence import EvidenceGraph
from sentinel.types import Claim, ClaimStatus, Conflict, Evidence

logger = logging.getLogger("sentinel.agents.verifier")

class VerifierAgent:
    """Independently verifies claims, audits evidence citations, and detects conflicts."""

    @classmethod
    def verify(
        cls, claims: List[Claim], evidence: List[Evidence]
    ) -> Tuple[List[Claim], List[Conflict]]:
        graph = EvidenceGraph()
        for ev in evidence:
            graph.add_evidence(ev)

        # 1. Audit evidence grounding for each claim
        for claim in claims:
            grounding_status = graph.verify_claim_grounding(claim)
            claim.status = grounding_status

        # 2. Cross-examination & conflict detection
        conflicts = ConflictDetector.detect_conflicts(claims)

        # 3. Mark conflicting claims as disputed until targeted resolution
        for conflict in conflicts:
            for cid in conflict.claim_ids:
                for c in claims:
                    if c.id == cid:
                        c.status = ClaimStatus.DISPUTED
                        c.divergence_reason = conflict.diverging_assumption

        return claims, conflicts
