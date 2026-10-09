from __future__ import annotations

import asyncio
import pytest
from sentinel.reliability.confidence import ConfidenceEngine
from sentinel.reliability.conflicts import ConflictDetector
from sentinel.reliability.evidence import EvidenceGraph
from sentinel.reliability.policy import PolicyEngine
from sentinel.reliability.postconditions import PostconditionValidator
from sentinel.types import (
    Action,
    Claim,
    ClaimStatus,
    Conflict,
    ConflictSeverity,
    ConflictStatus,
    Evidence,
    EvidenceType,
    RiskLevel,
)

def test_confidence_engine_bounds_and_weights():
    # Empty claims should give 0
    empty_conf = ConfidenceEngine.calculate([], [], [])
    assert empty_conf.overall == 0.0

    # Strong evidence + agreement + verification
    c1 = Claim(
        id="C1",
        statement="Durable Objects guarantee strongly consistent state",
        confidence=0.9,
        status=ClaimStatus.VERIFIED,
        evidence_ids=["E1"],
    )
    ev1 = Evidence(
        id="E1",
        type=EvidenceType.DOCUMENTATION,
        source="docs",
        content="Official DO docs",
        confidence=0.95,
        supports_claims=["C1"],
    )

    high_conf = ConfidenceEngine.calculate([c1], [ev1], [], execution_passed=True)
    assert 0.85 <= high_conf.overall <= 1.0
    assert high_conf.evidence_quality > 0.8
    assert high_conf.agent_agreement > 0.8
    assert high_conf.verification_success == 1.0

def test_confidence_engine_penalizes_conflicts_and_missing_evidence():
    # Claim without evidence and with an open conflict
    c1 = Claim(
        id="C1",
        statement="Unsubstantiated claim",
        confidence=0.5,
        status=ClaimStatus.DISPUTED,
        evidence_ids=[],
    )
    conflict = Conflict(
        id="CONF-01",
        claim_ids=["C1"],
        reason="Dispute",
        diverging_assumption="Unknown",
        severity=ConflictSeverity.HIGH,
        resolution_status=ConflictStatus.OPEN,
    )
    conf = ConfidenceEngine.calculate([c1], [], [conflict], execution_passed=False)
    # Overall confidence must be heavily penalized
    assert conf.overall < 0.35
    assert conf.evidence_quality < 0.2

def test_conflict_detector_identifies_opposing_premises():
    claims = [
        Claim(
            id="C1",
            statement="We must use Durable Objects for strongly coordinated real-time state.",
            agent_ids=["Agent A"],
        ),
        Claim(
            id="C2",
            statement="D1 is sufficient for our application without real-time coordination.",
            agent_ids=["Agent B"],
        ),
    ]
    conflicts = ConflictDetector.detect_conflicts(claims)
    assert len(conflicts) >= 1
    assert "CONF-001" == conflicts[0].id
    assert "coordinated" in conflicts[0].diverging_assumption.lower()

def test_evidence_graph_grounding_audit():
    graph = EvidenceGraph()
    c_verified = Claim(id="C1", statement="Grounded fact", confidence=0.9)
    c_unsupported = Claim(id="C2", statement="Hallucinated statement", confidence=0.9)

    ev = Evidence(
        id="E1",
        type=EvidenceType.DOCUMENTATION,
        source="cf-docs",
        content="Official proof",
        confidence=0.96,
        supports_claims=["C1"],
    )
    graph.add_evidence(ev)

    status_1 = graph.verify_claim_grounding(c_verified)
    status_2 = graph.verify_claim_grounding(c_unsupported)

    assert status_1 == ClaimStatus.VERIFIED
    assert status_2 == ClaimStatus.UNVERIFIED

def test_policy_engine_risk_and_gating():
    # Read query -> allowed without approval
    read_action = Action(
        id="A1",
        type="github.get_file",
        target="atishayj2202/sentinel",
        parameters={"path": "README.md"},
    )
    decision_read = PolicyEngine.evaluate(read_action)
    assert decision_read.allowed is True
    assert decision_read.risk == RiskLevel.LOW
    assert decision_read.requires_approval is False

    # Issue creation -> gated with human approval
    issue_action = Action(
        id="A2",
        type="github.create_issue",
        target="atishayj2202/sentinel",
        parameters={"title": "ADR"},
    )
    decision_issue = PolicyEngine.evaluate(issue_action)
    assert decision_issue.risk == RiskLevel.MEDIUM
    assert decision_issue.requires_approval is True
    assert issue_action.requires_approval is True

    # Production deploy -> critical gate
    deploy_action = Action(id="A3", type="deployment.production", target="prod-cluster")
    decision_deploy = PolicyEngine.evaluate(deploy_action)
    assert decision_deploy.risk == RiskLevel.CRITICAL
    assert decision_deploy.requires_approval is True

def test_postcondition_validator_detects_mismatch():
    class MockLiveSystem:
        async def get_issue(self, repo: str, num: int):
            # Returns an issue with a DIFFERENT title than expected
            return {"exists": True, "title": "Old Wrong Title"}

    action = Action(
        id="A1",
        type="github.create_issue",
        target="repo/name",
        executed=True,
        expected_outcome={"title": "Expected New Title"},
        actual_outcome={"issue_number": 42, "repo": "repo/name"},
    )

    async def run():
        return await PostconditionValidator.validate(action, MockLiveSystem())

    passed = asyncio.run(run())
    assert passed is False
    assert action.postcondition_verified is False
