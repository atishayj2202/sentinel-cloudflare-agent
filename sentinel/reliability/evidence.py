from __future__ import annotations

from typing import Dict, List, Set
from sentinel.types import Claim, ClaimStatus, Evidence

class EvidenceGraph:
    """Manages the bipartite graph connecting Claims to concrete Evidence."""

    def __init__(self) -> None:
        self.evidence_by_id: Dict[str, Evidence] = {}
        self.claim_to_evidence: Dict[str, Set[str]] = {}
        self.evidence_to_claim: Dict[str, Set[str]] = {}

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence_by_id[ev.id] = ev
        if ev.id not in self.evidence_to_claim:
            self.evidence_to_claim[ev.id] = set()
        for cid in ev.supports_claims:
            self.evidence_to_claim[ev.id].add(cid)
            if cid not in self.claim_to_evidence:
                self.claim_to_evidence[cid] = set()
            self.claim_to_evidence[cid].add(ev.id)

    def link(self, claim_id: str, evidence_id: str) -> None:
        if claim_id not in self.claim_to_evidence:
            self.claim_to_evidence[claim_id] = set()
        self.claim_to_evidence[claim_id].add(evidence_id)

        if evidence_id not in self.evidence_to_claim:
            self.evidence_to_claim[evidence_id] = set()
        self.evidence_to_claim[evidence_id].add(claim_id)

    def verify_claim_grounding(self, claim: Claim) -> ClaimStatus:
        """Rule 1: No unsupported important claim."""
        ev_ids = self.claim_to_evidence.get(claim.id, set())
        if not ev_ids:
            return ClaimStatus.UNVERIFIED
        
        ev_scores = [
            self.evidence_by_id[eid].confidence
            for eid in ev_ids
            if eid in self.evidence_by_id
        ]
        if not ev_scores:
            return ClaimStatus.UNVERIFIED

        avg_score = sum(ev_scores) / len(ev_scores)
        if avg_score >= 0.75 and len(ev_scores) >= 1:
            return ClaimStatus.VERIFIED
        elif avg_score >= 0.5:
            return ClaimStatus.UNVERIFIED
        else:
            return ClaimStatus.DISPUTED
