from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from sentinel.agents.analyst import AnalystAgent
from sentinel.agents.planner import PlannerAgent
from sentinel.agents.researcher import ResearcherAgent
from sentinel.agents.targeted import TargetedVerificationAgent
from sentinel.agents.verifier import VerifierAgent
from sentinel.config import config
from sentinel.orchestrator.state_machine import mission_store
from sentinel.reliability.confidence import ConfidenceEngine
from sentinel.reliability.policy import PolicyEngine
from sentinel.reliability.postconditions import PostconditionValidator
from sentinel.tools.github_tool import github_tool
from sentinel.types import (
    Action,
    Claim,
    ClaimStatus,
    Conflict,
    Evidence,
    Mission,
    MissionStatus,
    PolicyDecision,
    Subtask,
)

logger = logging.getLogger("sentinel.orchestrator.workflow")

class MissionWorkflow:
    """Coordinates durable multi-agent mission execution and verification."""

    def __init__(self) -> None:
        self.store = mission_store

    async def start_mission(
        self,
        user_request: str,
        on_update: Optional[Callable[[Mission], Any]] = None,
        auto_approve: bool = False,
    ) -> Mission:
        mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
        mission = Mission(
            id=mission_id,
            user_request=user_request,
            objective=f"Analyze and verify: {user_request}",
            status=MissionStatus.PLANNING,
        )
        self.store.save(mission)
        self.store.metrics.total_missions += 1
        await self._notify(mission, on_update)

        # 1. Planning Phase
        subtasks = await PlannerAgent.plan(user_request)
        mission.subtasks = subtasks
        mission.status = MissionStatus.RESEARCHING
        self.store.save(mission)
        await self._notify(mission, on_update)

        # 2. Parallel Investigation Phase
        research_tasks = [
            ResearcherAgent.investigate(st, st.assigned_agent)
            for st in subtasks
        ]
        results = await asyncio.gather(*research_tasks, return_exceptions=False)

        all_claims: List[Claim] = []
        all_evidence: List[Evidence] = []
        for claims_chunk, evidence_chunk in results:
            all_claims.extend(claims_chunk)
            all_evidence.extend(evidence_chunk)

        mission.claims = all_claims
        mission.evidence = all_evidence
        mission.status = MissionStatus.VERIFYING
        self.store.save(mission)
        await self._notify(mission, on_update)

        # 3. Verification & Conflict Detection Phase
        verified_claims, conflicts = VerifierAgent.verify(mission.claims, mission.evidence)
        mission.claims = verified_claims
        mission.conflicts = conflicts
        self.store.metrics.total_important_claims += len(mission.claims)

        # 4. Adaptive Disagreement Resolution (Signature feature!)
        if conflicts:
            mission.status = MissionStatus.TARGETED_RESEARCH
            self.store.save(mission)
            await self._notify(mission, on_update)
            self.store.metrics.conflicts_detected += len(conflicts)

            for conflict in conflicts:
                resolved_claim, resolved_ev = await TargetedVerificationAgent.resolve_conflict(
                    conflict, user_request
                )
                mission.claims.append(resolved_claim)
                mission.evidence.append(resolved_ev)
                self.store.metrics.conflicts_resolved += 1
                
                # Mark original claims as clarified/verified post-resolution
                for cid in conflict.claim_ids:
                    for c in mission.claims:
                        if c.id == cid:
                            c.status = ClaimStatus.VERIFIED
                            c.divergence_reason = f"Clarified: {conflict.resolution_summary}"

        # Update verified/unsupported claim metrics
        v_count = sum(1 for c in mission.claims if c.status == ClaimStatus.VERIFIED)
        u_count = sum(1 for c in mission.claims if c.status == ClaimStatus.UNVERIFIED)
        self.store.metrics.verified_claims += v_count
        self.store.metrics.unsupported_claims += u_count

        # 5. Deterministic Confidence Calculation
        mission.status = MissionStatus.CONFIDENCE_CALCULATION
        conf_breakdown = ConfidenceEngine.calculate(
            mission.claims, mission.evidence, mission.conflicts
        )
        mission.confidence = conf_breakdown
        self.store.save(mission)
        await self._notify(mission, on_update)

        # 6. Synthesis by Analyst Agent
        synthesis = await AnalystAgent.synthesize(
            user_request, mission.claims, mission.evidence
        )
        mission.recommendation = synthesis.get("recommendation")
        mission.tradeoffs = synthesis.get("tradeoffs", [])
        mission.unresolved_uncertainties = synthesis.get("uncertainties", [])

        # 7. Action Proposal & Policy Evaluation
        suggested_action = synthesis.get("suggested_action")
        if suggested_action:
            action_id = f"ACT-{uuid.uuid4().hex[:4].upper()}"
            action = Action(
                id=action_id,
                type=suggested_action.get("type", "github.create_issue"),
                target=config.GITHUB_DEFAULT_REPO,
                parameters={
                    "title": suggested_action.get("title", "Sentinel Architecture Decision"),
                    "body": suggested_action.get("body", "Documented decision"),
                },
                expected_outcome={
                    "issue_exists": True,
                    "title": suggested_action.get("title", "Sentinel Architecture Decision"),
                },
            )

            # Evaluate against Engineering Codex
            policy_decision = PolicyEngine.evaluate(action)
            mission.actions.append(action)

            if policy_decision.requires_approval:
                self.store.metrics.total_side_effects += 1
                self.store.metrics.gated_side_effects += 1
                mission.status = MissionStatus.AWAITING_APPROVAL
                self.store.save(mission)
                await self._notify(mission, on_update)

                if auto_approve:
                    # In test/batch mode, trigger automatic approval
                    await self.approve_action(mission.id, action.id, on_update)
                    return mission
                else:
                    # Pause workflow and await operator interaction
                    return mission
            else:
                # Read-only or safe action: auto-execute
                await self._execute_action_step(mission, action)

        mission.status = MissionStatus.COMPLETED
        self.store.metrics.successful_missions += 1
        self.store.save(mission)
        await self._notify(mission, on_update)
        return mission

    async def approve_action(
        self,
        mission_id: str,
        action_id: str,
        on_update: Optional[Callable[[Mission], Any]] = None,
    ) -> Mission:
        """Human approval callback that resumes the workflow."""
        mission = self.store.get(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        action = next((a for a in mission.actions if a.id == action_id), None)
        if not action:
            raise ValueError(f"Action {action_id} not found in mission {mission_id}")

        action.approved = True
        mission.status = MissionStatus.EXECUTING
        self.store.save(mission)
        await self._notify(mission, on_update)

        await self._execute_action_step(mission, action)

        mission.status = MissionStatus.COMPLETED
        self.store.metrics.successful_missions += 1
        self.store.save(mission)
        await self._notify(mission, on_update)
        return mission

    async def reject_action(
        self,
        mission_id: str,
        action_id: str,
        on_update: Optional[Callable[[Mission], Any]] = None,
    ) -> Mission:
        """Human rejection stops execution safely without side effects."""
        mission = self.store.get(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        action = next((a for a in mission.actions if a.id == action_id), None)
        if action:
            action.approved = False
            action.executed = False

        mission.status = MissionStatus.COMPLETED
        self.store.metrics.successful_missions += 1
        self.store.save(mission)
        await self._notify(mission, on_update)
        return mission

    async def _execute_action_step(self, mission: Mission, action: Action) -> None:
        """Durable execution with retry backoff and closed-loop validation."""
        max_retries = 2
        retry_delay = 0.05

        for attempt in range(max_retries + 1):
            action.retry_count = attempt
            try:
                if action.type == "github.create_issue":
                    res = await github_tool.create_issue(
                        repo=action.target,
                        title=action.parameters["title"],
                        body=action.parameters["body"],
                    )
                    action.actual_outcome = res
                    action.executed = True
                    break
            except Exception as e:
                logger.warning(
                    f"Action {action.id} attempt {attempt+1} failed: {e}. Retrying durable step..."
                )
                self.store.metrics.total_injected_failures += 1
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    self.store.metrics.recovered_failures += 1
                    continue
                else:
                    action.error_message = str(e)
                    action.executed = False
                    mission.status = MissionStatus.REPLANNING
                    return

        # Closed-loop postcondition verification
        mission.status = MissionStatus.VALIDATING
        self.store.metrics.postconditions_checked += 1
        passed = await PostconditionValidator.validate(action, github_tool)
        if passed:
            self.store.metrics.postconditions_passed += 1
        else:
            mission.status = MissionStatus.FAILED

    async def _notify(
        self, mission: Mission, callback: Optional[Callable[[Mission], Any]]
    ) -> None:
        if callback:
            try:
                res = callback(mission)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

mission_workflow = MissionWorkflow()
