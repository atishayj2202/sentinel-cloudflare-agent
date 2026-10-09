from __future__ import annotations

from typing import Dict
from sentinel.types import Action, PolicyDecision, RiskLevel

class PolicyEngine:
    """Enforces Cloudflare Engineering Codex policies and human approval gates."""

    CODEX_RULES: Dict[str, Dict[str, object]] = {
        # Read operations
        "github.search": {
            "risk": RiskLevel.NONE,
            "requires_approval": False,
            "rule": "CODEX-SEC-01",
            "reason": "Safe idempotent read query",
        },
        "github.get_issue": {
            "risk": RiskLevel.NONE,
            "requires_approval": False,
            "rule": "CODEX-SEC-01",
            "reason": "Safe idempotent read query",
        },
        "github.get_file": {
            "risk": RiskLevel.LOW,
            "requires_approval": False,
            "rule": "CODEX-SEC-01",
            "reason": "Repository inspection allowed without mutation",
        },
        "web.search": {
            "risk": RiskLevel.LOW,
            "requires_approval": False,
            "rule": "CODEX-SEC-02",
            "reason": "External documentation retrieval is read-only",
        },
        # Side effects
        "github.create_issue": {
            "risk": RiskLevel.MEDIUM,
            "requires_approval": True,
            "rule": "CODEX-GITOPS-04",
            "reason": "Public side-effect on repository requires human operator confirmation",
        },
        "github.update_file": {
            "risk": RiskLevel.HIGH,
            "requires_approval": True,
            "rule": "CODEX-GITOPS-07",
            "reason": "Direct code modification introduces regression risk",
        },
        "deployment.production": {
            "risk": RiskLevel.CRITICAL,
            "requires_approval": True,
            "rule": "CODEX-REL-01",
            "reason": "Production deployments require signed authorization",
        },
    }

    @classmethod
    def evaluate(cls, action: Action) -> PolicyDecision:
        rule_meta = cls.CODEX_RULES.get(action.type)
        if not rule_meta:
            # Default strict fallback for unknown action types
            return PolicyDecision(
                action_type=action.type,
                allowed=True,
                risk=RiskLevel.HIGH,
                requires_approval=True,
                codex_rule="CODEX-DEFAULT-RESTRICT",
                reason=f"Action '{action.type}' is unrecognized and gated by default high-risk policy",
            )

        risk = rule_meta["risk"]
        requires_approval = bool(rule_meta["requires_approval"])
        codex_rule = str(rule_meta["rule"])
        reason = str(rule_meta["reason"])

        # Update action properties
        action.risk = risk
        action.requires_approval = requires_approval

        return PolicyDecision(
            action_type=action.type,
            allowed=True,
            risk=risk,
            requires_approval=requires_approval,
            codex_rule=codex_rule,
            reason=reason,
        )
