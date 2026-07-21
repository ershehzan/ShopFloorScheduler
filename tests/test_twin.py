"""
tests/test_twin.py
Tests for Phase 4 Digital Twin simulation module.

Covers:
  - DigitalTwin: initialization, event generation, schedule parsing
  - SimEvent: serialization
  - API endpoints: start session, list sessions, inject disruption
"""
import json
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# SimEvent tests
# ---------------------------------------------------------------------------

class TestSimEvent:
    def test_to_dict_includes_required_fields(self):
        from twin.simulator import SimEvent
        event = SimEvent(
            event_type="op_start",
            virtual_time=10.0,
            payload={"job_id": 1, "machine_id": "M1"},
        )
        d = event.to_dict()
        assert d["event_type"] == "op_start"
        assert d["virtual_time"] == 10.0
        assert d["payload"]["job_id"] == 1
        assert "real_timestamp" in d

    def test_all_event_types_serializable(self):
        from twin.simulator import SimEvent
        event_types = ["op_start", "op_end", "machine_alert", "breakdown", "rush_order", "sim_complete"]
        for et in event_types:
            event = SimEvent(event_type=et, virtual_time=0.0, payload={})
            d = event.to_dict()
            assert d["event_type"] == et


# ---------------------------------------------------------------------------
# DigitalTwin tests
# ---------------------------------------------------------------------------

class TestDigitalTwin:
    @pytest.fixture
    def sample_schedule(self):
        """Minimal schedule: 2 jobs, 2 machines, 2 ops each."""
        return [
            (1, 0, 1, 0.0, 10.0),
            (1, 1, 2, 10.0, 18.0),
            (2, 0, 2, 0.0, 5.0),
            (2, 1, 1, 10.0, 22.0),
        ]

    def test_initialization(self, sample_schedule):
        from twin.simulator import DigitalTwin
        twin = DigitalTwin(sample_schedule, "sess_1", speed_factor=1000.0)
        assert twin.session_id == "sess_1"
        assert not twin.is_running

    def test_machine_ids_extracted_from_schedule(self, sample_schedule):
        from twin.simulator import DigitalTwin
        twin = DigitalTwin(sample_schedule, "sess_2", speed_factor=1000.0)
        assert "1" in twin._machine_ids or 1 in twin._machine_ids

    def test_schedule_sorted_by_start_time(self, sample_schedule):
        from twin.simulator import DigitalTwin
        # Shuffle the schedule
        import random
        shuffled = random.sample(sample_schedule, len(sample_schedule))
        twin = DigitalTwin(shuffled, "sess_3", speed_factor=1000.0)
        starts = [op[3] for op in twin.schedule]
        assert starts == sorted(starts)

    @pytest.mark.asyncio
    async def test_run_emits_events(self, sample_schedule):
        from twin.simulator import DigitalTwin
        events = []

        async def collect(session_id, event):
            events.append(event)

        twin = DigitalTwin(
            sample_schedule, "sess_4", speed_factor=10000.0, inject_failures=False
        )
        await twin.run(collect)

        event_types = {e["event_type"] for e in events}
        assert "op_start" in event_types
        assert "op_end" in event_types
        assert "sim_complete" in event_types

    @pytest.mark.asyncio
    async def test_run_emits_sim_complete(self, sample_schedule):
        from twin.simulator import DigitalTwin
        events = []

        async def collect(session_id, event):
            events.append(event)

        twin = DigitalTwin(sample_schedule, "sess_5", speed_factor=10000.0, inject_failures=False)
        await twin.run(collect)
        last = events[-1]
        assert last["event_type"] == "sim_complete"

    @pytest.mark.asyncio
    async def test_inject_disruption_breakdown(self, sample_schedule):
        from twin.simulator import DigitalTwin
        events = []

        async def collect(session_id, event):
            events.append(event)

        twin = DigitalTwin(sample_schedule, "sess_6", speed_factor=10000.0, inject_failures=False)

        # Inject a breakdown before running
        await twin.inject_disruption({
            "disruption_type": "breakdown",
            "machine_id": "1",
            "duration": 15.0,
            "at_time": 0.0,
        })

        await twin.run(collect)
        # Should have processed the breakdown disruption
        types = [e["event_type"] for e in events]
        assert "breakdown" in types

    @pytest.mark.asyncio
    async def test_is_not_running_after_completion(self, sample_schedule):
        from twin.simulator import DigitalTwin
        twin = DigitalTwin(sample_schedule, "sess_7", speed_factor=10000.0, inject_failures=False)
        await twin.run(lambda s, e: asyncio.sleep(0))
        assert not twin.is_running

    def test_severity_classification(self):
        from twin.simulator import _classify_severity
        assert _classify_severity(0.9) == "critical"
        assert _classify_severity(0.7) == "high"
        assert _classify_severity(0.4) == "medium"
        assert _classify_severity(0.1) == "low"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestTwinAPI:
    def test_list_sessions_empty(self, client):
        response = client.get("/api/twin/sessions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_start_session_unknown_task(self, client):
        response = client.post(
            "/api/twin/start/nonexistent-task-id",
            json={"task_id": "nonexistent-task-id", "speed_factor": 100.0},
        )
        assert response.status_code == 404

    def test_stop_session_not_found(self, client):
        response = client.delete("/api/twin/sessions/nonexistent-session")
        assert response.status_code == 404

    def test_inject_disruption_nonexistent_session(self, client):
        response = client.post(
            "/api/twin/sessions/bad_session/inject",
            json={"disruption_type": "breakdown", "machine_id": "M1"},
        )
        assert response.status_code == 404
