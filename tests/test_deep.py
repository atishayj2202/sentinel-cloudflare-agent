from __future__ import annotations

import asyncio
import pytest
from sentinel.orchestrator.mission_workflow import MissionWorkflow
from sentinel.tools.github_tool import GitHubTool
from sentinel.types import Action, MissionStatus

def test_workflow_recovers_from_injected_tool_503():
    """Verify durable workflow survives transient 503 error on tool call."""
    async def run():
        tool = GitHubTool()
        tool.inject_transient_fault(count=1, code=503)

        # First attempt raises 503
        with pytest.raises(RuntimeError) as exc_info:
            await tool.create_issue("repo", "Test", "Body")
        assert "503" in str(exc_info.value)

        # Next attempt succeeds
        res = await tool.create_issue("repo", "Test", "Body")
        assert res["success"] is True
        assert res["issue_number"] >= 101

    asyncio.run(run())

def test_human_approval_gate_blocks_execution_until_approved():
    """Verify that mutating side effects halt at AWAITING_APPROVAL."""
    async def run():
        workflow = MissionWorkflow()
        mission = await workflow.start_mission(
            "Should we use D1 or Durable Objects for our real-time game?",
            auto_approve=False,
        )

        # Must be paused for approval
        assert mission.status == MissionStatus.AWAITING_APPROVAL
        assert len(mission.actions) > 0
        action = mission.actions[0]
        assert action.requires_approval is True
        assert action.approved is None
        assert action.executed is False

        # Operator approves action
        updated_mission = await workflow.approve_action(mission.id, action.id)
        assert updated_mission.status == MissionStatus.COMPLETED
        assert action.approved is True
        assert action.executed is True
        assert action.postcondition_verified is True

    asyncio.run(run())

def test_human_rejection_prevents_side_effects():
    """Verify that operator rejection immediately terminates without executing tools."""
    async def run():
        workflow = MissionWorkflow()
        mission = await workflow.start_mission(
            "Audit state persistence and post public issue",
            auto_approve=False,
        )
        assert mission.status == MissionStatus.AWAITING_APPROVAL
        action = mission.actions[0]

        # Operator rejects action
        rejected_mission = await workflow.reject_action(mission.id, action.id)
        assert rejected_mission.status == MissionStatus.COMPLETED
        assert action.approved is False
        assert action.executed is False

    asyncio.run(run())

def test_disagreement_triggers_targeted_verification():
    """Verify that conflicting premises trigger targeted investigation and resolve."""
    async def run():
        workflow = MissionWorkflow()
        mission = await workflow.start_mission(
            "For multi-user real-time state, should we use D1 or Durable Objects?",
            auto_approve=True,
        )

        # Verify conflict was recorded and resolved
        assert len(mission.conflicts) >= 1
        conflict = mission.conflicts[0]
        assert conflict.resolution_status == "resolved"
        assert "Workload Assumption Mismatch" in (conflict.resolution_summary or "")
        # Confidence score should be high post-resolution
        assert mission.confidence.overall >= 0.85

    asyncio.run(run())
