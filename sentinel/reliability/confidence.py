from __future__ import annotations

from typing import List, Optional
from sentinel.types import Claim, ClaimStatus, ConfidenceBreakdown, Evidence, Conflict

class ConfidenceEngine:
    """Calculates deterministic, explainable system confidence."""

    WEIGHT_EVIDENCE = 0.35
    WEIGHT_AGREEMENT = 0.30
    WEIGHT_VERIFICATION = 0.20
    WEIGHT_EXECUTION = 0.15

    @classmethod
    def calculate(
        cls,
        claims: List[Claim],
        evidence: List[Evidence],
        conflicts: List[Conflict],
        execution_passed: Optional[bool] = None,
    ) -> ConfidenceBreakdown:
        if not claims:
            return ConfidenceBreakdown(overall=0.0)

        # 1. Evidence Quality (0.0 to 1.0)
        # Average confidence of evidence pieces linked to claims, penalized if claims lack evidence
        if evidence:
            avg_ev_quality = sum(e.confidence for e in evidence) / len(evidence)
            claims_with_evidence = sum(1 for c in claims if len(c.evidence_ids) > 0)
            evidence_coverage = claims_with_evidence / len(claims)
            evidence_score = (avg_ev_quality * 0.7) + (evidence_coverage * 0.3)
        else:
            evidence_score = 0.1

        # 2. Agent Agreement (0.0 to 1.0)
        # Penalized heavily by unresolved conflicts
        open_conflicts = [c for c in conflicts if c.resolution_status != "resolved"]
        if not open_conflicts:
            agreement_score = 0.95
        else:
            penalty = len(open_conflicts) * 0.25
            agreement_score = max(0.1, 0.95 - penalty)

        # 3. Verification Success (0.0 to 1.0)
        # Ratio of verified claims vs disputed/unverified
        verified_count = sum(1 for c in claims if c.status == ClaimStatus.VERIFIED)
        disputed_count = sum(1 for c in claims if c.status == ClaimStatus.DISPUTED)
        rejected_count = sum(1 for c in claims if c.status == ClaimStatus.REJECTED)

        total_claims = len(claims)
        verification_score = max(
            0.0,
            (verified_count * 1.0 - disputed_count * 0.5 - rejected_count * 0.8)
            / total_claims,
        )

        # 4. Execution Success (0.0 to 1.0)
        if execution_passed is None:
            # Rebalance weights for research-only evaluation
            w_ev = 0.40
            w_ag = 0.35
            w_ver = 0.25
            overall = (evidence_score * w_ev) + (agreement_score * w_ag) + (verification_score * w_ver)
            execution_score = 1.0
        else:
            execution_score = 1.0 if execution_passed else 0.0
            overall = (
                (evidence_score * cls.WEIGHT_EVIDENCE)
                + (agreement_score * cls.WEIGHT_AGREEMENT)
                + (verification_score * cls.WEIGHT_VERIFICATION)
                + (execution_score * cls.WEIGHT_EXECUTION)
            )

        # Ensure within bounds [0.0, 1.0]
        overall = max(0.0, min(1.0, round(overall, 4)))

        return ConfidenceBreakdown(
            overall=overall,
            evidence_quality=round(evidence_score, 4),
            agent_agreement=round(agreement_score, 4),
            verification_success=round(verification_score, 4),
            execution_success=round(execution_score, 4),
            formula_explanation=(
                f"Evidence: {int(evidence_score*100)}% | "
                f"Agreement: {int(agreement_score*100)}% | "
                f"Verification: {int(verification_score*100)}% | "
                f"Overall: {int(overall*100)}%"
            ),
        )
