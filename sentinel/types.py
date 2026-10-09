from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class MissionStatus(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    RESEARCHING = "researching"
    VERIFYING = "verifying"
    TARGETED_RESEARCH = "targeted_research"
    CONFIDENCE_CALCULATION = "confidence_calculation"
    POLICY_CHECK = "policy_check"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    REPLANNING = "replanning"

class EvidenceType(str, Enum):
    DOCUMENTATION = "documentation"
    BENCHMARK = "benchmark"
    CODE_OBSERVATION = "code_observation"
    TOOL_OUTPUT = "tool_output"
    RUNTIME_METRIC = "runtime_metric"

class Evidence(BaseModel):
    id: str
    type: EvidenceType = EvidenceType.DOCUMENTATION
    source: str
    content: str
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    supports_claims: List[str] = Field(default_factory=list)
    retrieved_by: str = "Researcher"
    timestamp: float = Field(default_factory=time.time)

class ClaimStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    REJECTED = "rejected"

class Claim(BaseModel):
    id: str
    statement: str
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    evidence_ids: List[str] = Field(default_factory=list)
    agent_ids: List[str] = Field(default_factory=list)
    divergence_reason: Optional[str] = None

class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ConflictStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"

class Conflict(BaseModel):
    id: str
    claim_ids: List[str]
    agent_ids: List[str] = Field(default_factory=list)
    reason: str
    diverging_assumption: str
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    resolution_status: ConflictStatus = ConflictStatus.OPEN
    resolution_summary: Optional[str] = None

class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class PolicyDecision(BaseModel):
    action_type: str
    allowed: bool
    risk: RiskLevel
    requires_approval: bool = False
    codex_rule: str
    reason: str

class Action(BaseModel):
    id: str
    type: str
    target: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    approved: Optional[bool] = None
    executed: bool = False
    expected_outcome: Dict[str, Any] = Field(default_factory=dict)
    actual_outcome: Optional[Dict[str, Any]] = None
    postcondition_verified: Optional[bool] = None
    error_message: Optional[str] = None
    retry_count: int = 0

class Subtask(BaseModel):
    id: str
    type: str = "research"
    question: str
    assigned_agent: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None

class ConfidenceBreakdown(BaseModel):
    overall: float = 0.0
    evidence_quality: float = 0.0
    agent_agreement: float = 0.0
    verification_success: float = 0.0
    execution_success: float = 0.0
    formula_explanation: str = "35% Evidence + 30% Agreement + 20% Verification + 15% Execution"

class Mission(BaseModel):
    id: str
    user_request: str
    objective: str
    status: MissionStatus = MissionStatus.IDLE
    subtasks: List[Subtask] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    actions: List[Action] = Field(default_factory=list)
    confidence: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    recommendation: Optional[str] = None
    tradeoffs: List[str] = Field(default_factory=list)
    unresolved_uncertainties: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

class ReliabilityMetrics(BaseModel):
    total_missions: int = 0
    successful_missions: int = 0
    total_important_claims: int = 0
    verified_claims: int = 0
    unsupported_claims: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    total_side_effects: int = 0
    gated_side_effects: int = 0
    total_injected_failures: int = 0
    recovered_failures: int = 0
    postconditions_checked: int = 0
    postconditions_passed: int = 0

    @property
    def mission_success_rate(self) -> float:
        return (self.successful_missions / self.total_missions) if self.total_missions > 0 else 1.0

    @property
    def verified_decision_rate(self) -> float:
        if self.total_important_claims > 0:
            return min(1.0, self.verified_claims / self.total_important_claims)
        return 1.0

    @property
    def unsupported_claim_rate(self) -> float:
        return (self.unsupported_claims / self.total_important_claims) if self.total_important_claims > 0 else 0.0

    @property
    def recovery_success_rate(self) -> float:
        return (self.recovered_failures / self.total_injected_failures) if self.total_injected_failures > 0 else 1.0

    @property
    def approval_accuracy(self) -> float:
        return (self.gated_side_effects / self.total_side_effects) if self.total_side_effects > 0 else 1.0
