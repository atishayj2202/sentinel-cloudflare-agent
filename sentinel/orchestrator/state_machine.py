from __future__ import annotations

import time
from typing import Dict, List, Optional
from sentinel.types import Mission, MissionStatus, ReliabilityMetrics

class MissionStore:
    """State store for missions and reliability tracking."""

    def __init__(self) -> None:
        self.missions: Dict[str, Mission] = {}
        self.metrics: ReliabilityMetrics = ReliabilityMetrics()

    def get(self, mission_id: str) -> Optional[Mission]:
        return self.missions.get(mission_id)

    def save(self, mission: Mission) -> None:
        mission.updated_at = time.time()
        self.missions[mission.id] = mission

    def update_status(self, mission_id: str, status: MissionStatus) -> None:
        m = self.get(mission_id)
        if m:
            m.status = status
            m.updated_at = time.time()

    def list_missions(self) -> List[Mission]:
        return sorted(self.missions.values(), key=lambda m: m.created_at, reverse=True)

mission_store = MissionStore()
