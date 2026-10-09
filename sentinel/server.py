from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sentinel.config import config
from sentinel.orchestrator.mission_workflow import mission_workflow
from sentinel.orchestrator.state_machine import mission_store
from sentinel.tools.github_tool import github_tool
from sentinel.types import Mission

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel.server")

app = FastAPI(
    title="Sentinel",
    description="Self-Verifying Autonomous Agent on Cloudflare",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: Set[WebSocket] = set()

async def broadcast_mission(mission: Mission) -> None:
    if not active_connections:
        return
    payload = json.dumps({"type": "mission_update", "data": mission.model_dump()})
    disconnected = set()
    for ws in active_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        active_connections.discard(ws)

class CreateMissionRequest(BaseModel):
    request: str
    auto_approve: bool = False

class ActionDecisionRequest(BaseModel):
    action_id: str

class SimulateFaultRequest(BaseModel):
    count: int = 1
    error_code: int = 503

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        # Send current metrics and recent missions on connect
        await websocket.send_text(
            json.dumps({
                "type": "init",
                "metrics": mission_store.metrics.model_dump(),
                "missions": [m.model_dump() for m in mission_store.list_missions()[:5]],
            })
        )
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            action = msg.get("action")
            if action == "start_mission":
                user_req = msg.get("request", "")
                await mission_workflow.start_mission(
                    user_req, on_update=broadcast_mission
                )
            elif action == "approve":
                m_id = msg.get("mission_id")
                act_id = msg.get("action_id")
                await mission_workflow.approve_action(m_id, act_id, on_update=broadcast_mission)
            elif action == "reject":
                m_id = msg.get("mission_id")
                act_id = msg.get("action_id")
                await mission_workflow.reject_action(m_id, act_id, on_update=broadcast_mission)
            elif action == "simulate_fault":
                github_tool.inject_transient_fault(count=1, code=503)
                await websocket.send_text(
                    json.dumps({
                        "type": "fault_injected",
                        "message": "Transient 503 fault injected for next tool execution.",
                    })
                )
    except WebSocketDisconnect:
        active_connections.discard(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)

@app.post("/api/missions")
async def create_mission(body: CreateMissionRequest):
    if not body.request.strip():
        raise HTTPException(status_code=400, detail="Mission request cannot be empty")
    mission = await mission_workflow.start_mission(
        body.request, on_update=broadcast_mission, auto_approve=body.auto_approve
    )
    return mission

@app.get("/api/missions")
async def get_missions():
    return mission_store.list_missions()

@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    m = mission_store.get(mission_id)
    if not m:
        raise HTTPException(status_code=404, detail="Mission not found")
    return m

@app.post("/api/missions/{mission_id}/approve")
async def approve_mission_action(mission_id: str, body: ActionDecisionRequest):
    try:
        return await mission_workflow.approve_action(
            mission_id, body.action_id, on_update=broadcast_mission
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/missions/{mission_id}/reject")
async def reject_mission_action(mission_id: str, body: ActionDecisionRequest):
    try:
        return await mission_workflow.reject_action(
            mission_id, body.action_id, on_update=broadcast_mission
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/simulate-fault")
async def simulate_fault(body: SimulateFaultRequest):
    github_tool.inject_transient_fault(count=body.count, code=body.error_code)
    return {
        "status": "injected",
        "count": body.count,
        "error_code": body.error_code,
        "message": "Simulated fault armed for next tool execution.",
    }

@app.get("/api/metrics")
async def get_metrics():
    return {
        "metrics": mission_store.metrics.model_dump(),
        "mission_success_rate": round(mission_store.metrics.mission_success_rate, 4),
        "verified_decision_rate": round(mission_store.metrics.verified_decision_rate, 4),
        "unsupported_claim_rate": round(mission_store.metrics.unsupported_claim_rate, 4),
        "recovery_success_rate": round(mission_store.metrics.recovery_success_rate, 4),
        "approval_accuracy": round(mission_store.metrics.approval_accuracy, 4),
    }

@app.get("/api/benchmarks")
async def get_benchmarks():
    report_file = Path(__file__).parent.parent / "tests" / "benchmark_report.json"
    if report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"scenarios_evaluated": 0, "scenario_results": [], "metrics": {}}

@app.post("/api/benchmarks/run")
async def trigger_benchmarks():
    try:
        from tests.benchmark_runner import run_benchmarks
        summary = await run_benchmarks()
        return summary
    except Exception as e:
        logger.error(f"Benchmark error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend static assets
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(frontend_dir / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sentinel.server:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
