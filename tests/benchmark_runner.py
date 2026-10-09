from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from sentinel.orchestrator.mission_workflow import MissionWorkflow
from sentinel.orchestrator.state_machine import mission_store
from sentinel.tools.github_tool import github_tool
from sentinel.types import ClaimStatus, MissionStatus

async def run_benchmarks() -> Dict[str, Any]:
    scenarios_path = Path(__file__).parent / "test_scenarios.json"
    with open(scenarios_path, "r", encoding="utf-8") as f:
        scenarios: List[Dict[str, Any]] = json.load(f)

    workflow = MissionWorkflow()
    print("\n" + "=" * 70)
    print("SENTINEL AI AGENT RELIABILITY BENCHMARK SUITE".center(70))
    print("=" * 70 + "\n")

    scenario_results: List[Dict[str, Any]] = []
    start_total_time = time.time()

    for idx, sc in enumerate(scenarios, 1):
        sc_id = sc["id"]
        name = sc["name"]
        prompt = sc["prompt"]
        inject_fault = sc.get("inject_fault", False)
        operator_reject = sc.get("operator_reject", False)

        print(f"[{idx}/{len(scenarios)}] Running {sc_id}: {name}...")
        t0 = time.time()

        if inject_fault:
            github_tool.inject_transient_fault(count=1, code=503)

        # Run mission
        mission = await workflow.start_mission(prompt, auto_approve=False)

        # Handle approval if awaiting
        if mission.status == MissionStatus.AWAITING_APPROVAL and mission.actions:
            action = mission.actions[0]
            if operator_reject:
                mission = await workflow.reject_action(mission.id, action.id)
            else:
                mission = await workflow.approve_action(mission.id, action.id)

        latency = round(time.time() - t0, 3)
        passed = mission.status == MissionStatus.COMPLETED

        status_str = "PASS" if passed else "FAIL"
        print(
            f"       -> Status: {status_str} | Latency: {latency}s | "
            f"Confidence: {int(mission.confidence.overall * 100)}% | "
            f"Claims: {len(mission.claims)} | Conflicts Resolved: {len(mission.conflicts)}"
        )

        scenario_results.append({
            "id": sc_id,
            "name": name,
            "passed": passed,
            "latency": latency,
            "confidence": mission.confidence.overall,
            "claims_count": len(mission.claims),
            "verified_claims": sum(1 for c in mission.claims if c.status == ClaimStatus.VERIFIED),
            "unsupported_claims": sum(1 for c in mission.claims if c.status == ClaimStatus.UNVERIFIED),
            "conflicts_count": len(mission.conflicts),
        })

    total_duration = round(time.time() - start_total_time, 2)
    metrics = mission_store.metrics

    print("\n" + "=" * 70)
    print("BENCHMARK EXECUTION SUMMARY".center(70))
    print("=" * 70)
    print(f"Missions Evaluated:           {len(scenarios)}")
    print(f"Mission Success Rate:         {metrics.mission_success_rate * 100:.1f}%")
    print(f"Verified Decision Rate:       {metrics.verified_decision_rate * 100:.1f}%")
    print(f"Unsupported Claim Rate:       {metrics.unsupported_claim_rate * 100:.1f}%")
    print(f"Transient Recovery Rate:      {metrics.recovery_success_rate * 100:.1f}%")
    print(f"Approval Gating Accuracy:     {metrics.approval_accuracy * 100:.1f}%")
    print(f"Postcondition Validation:     {metrics.postconditions_passed}/{metrics.postconditions_checked}")
    print(f"Total Benchmark Duration:     {total_duration}s")
    print("=" * 70 + "\n")

    summary = {
        "scenarios_evaluated": len(scenarios),
        "total_duration_sec": total_duration,
        "metrics": {
            "mission_success_rate": round(metrics.mission_success_rate, 4),
            "verified_decision_rate": round(metrics.verified_decision_rate, 4),
            "unsupported_claim_rate": round(metrics.unsupported_claim_rate, 4),
            "recovery_success_rate": round(metrics.recovery_success_rate, 4),
            "approval_accuracy": round(metrics.approval_accuracy, 4),
            "postconditions_passed": metrics.postconditions_passed,
            "postconditions_checked": metrics.postconditions_checked,
        },
        "scenario_results": scenario_results,
    }

    # Save benchmark report to file
    out_file = Path(__file__).parent / "benchmark_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary

if __name__ == "__main__":
    asyncio.run(run_benchmarks())
