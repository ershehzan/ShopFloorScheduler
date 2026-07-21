"""
twin/simulator.py
Discrete-event Digital Twin simulator (Phase 4).

The DigitalTwin takes a completed schedule (list of operation tuples) and
replays it in virtual time, emitting SimEvent objects through an asyncio queue.

Supported event types:
  - op_start       : An operation begins on a machine.
  - op_end         : An operation finishes.
  - machine_alert  : Machine health deteriorated; failure predicted soon.
  - breakdown      : Machine has broken down; affected operations paused.
  - rush_order     : A rush job has been injected.
  - sim_complete   : Simulation has reached the end of the schedule.

Events are streamed to connected WebSocket clients via the existing WS
connection manager in api/routers/ws.py.
"""
from __future__ import annotations

import asyncio
import datetime
import random
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------

@dataclass
class SimEvent:
    """A single discrete event emitted by the Digital Twin."""

    event_type: str           # "op_start" | "op_end" | "machine_alert" | "breakdown" | "rush_order" | "sim_complete"
    virtual_time: float       # Virtual clock time when this event occurs
    payload: Dict[str, Any]   # Event-specific data
    real_timestamp: str = ""  # Wall-clock ISO timestamp (set at emit time)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["real_timestamp"] = datetime.datetime.utcnow().isoformat()
        return d


# ---------------------------------------------------------------------------
# Digital Twin
# ---------------------------------------------------------------------------

class DigitalTwin:
    """
    Discrete-event simulator that replays a completed schedule in virtual time.

    The simulator converts the schedule's abstract time units into real wall-clock
    delays using `speed_factor` (e.g. speed_factor=10 → 1 time unit takes 0.1s).

    Disruptions (breakdowns, rush orders) can be injected at any point by
    calling `inject_disruption()` from another coroutine.
    """

    def __init__(
        self,
        schedule: List[Tuple],
        session_id: str,
        speed_factor: float = 10.0,
        inject_failures: bool = True,
        failure_seed: Optional[int] = None,
    ) -> None:
        """
        Args:
            schedule:        List of (job_id, op_index, machine_id, start, end) tuples.
            session_id:      Unique session identifier (used as WS channel key).
            speed_factor:    How many virtual time units pass per real second.
            inject_failures: If True, randomly inject machine alerts/breakdowns.
            failure_seed:    RNG seed for reproducible failure injection.
        """
        self.schedule = sorted(schedule, key=lambda x: x[3])  # sort by start_time
        self.session_id = session_id
        self.speed_factor = speed_factor
        self.inject_failures = inject_failures
        self._rng = random.Random(failure_seed)

        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._disruption_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._virtual_time: float = 0.0

        # Track pending breakdown windows: machine_id → end_time
        self._breakdowns: Dict[str, float] = {}

        # Collect all machine IDs from schedule
        self._machine_ids = sorted({str(op[2]) for op in self.schedule})

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def virtual_time(self) -> float:
        return self._virtual_time

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Public control API
    # ------------------------------------------------------------------

    async def run(self, emit_fn) -> None:
        """
        Main simulation coroutine.

        Args:
            emit_fn: async callable(session_id, event_dict) → broadcasts to WS subscribers.
        """
        self._running = True
        previous_time = 0.0

        for op in self.schedule:
            job_id, op_idx, machine_id, start_time, end_time = op
            machine_str = str(machine_id)

            # Advance virtual clock to start_time
            await self._advance_to(start_time, previous_time, emit_fn)
            previous_time = start_time

            # Check for pending breakdown at this machine
            if machine_str in self._breakdowns and self._breakdowns[machine_str] > start_time:
                # Skip this operation (machine is down)
                await emit_fn(self.session_id, SimEvent(
                    event_type="breakdown",
                    virtual_time=start_time,
                    payload={
                        "machine_id": machine_str,
                        "job_id": job_id,
                        "op_index": op_idx,
                        "message": f"Machine {machine_str} is broken; operation deferred.",
                    },
                ).to_dict())
                continue

            # Emit op_start
            await emit_fn(self.session_id, SimEvent(
                event_type="op_start",
                virtual_time=start_time,
                payload={
                    "job_id": job_id,
                    "op_index": op_idx,
                    "machine_id": machine_str,
                    "end_time": end_time,
                },
            ).to_dict())

            # Advance to end_time
            await self._advance_to(end_time, start_time, emit_fn)
            previous_time = end_time

            # Emit op_end
            await emit_fn(self.session_id, SimEvent(
                event_type="op_end",
                virtual_time=end_time,
                payload={
                    "job_id": job_id,
                    "op_index": op_idx,
                    "machine_id": machine_str,
                },
            ).to_dict())

            # Maybe inject a random failure alert
            if self.inject_failures and self._rng.random() < 0.04:
                target_machine = self._rng.choice(self._machine_ids)
                prob = round(self._rng.uniform(0.35, 0.95), 3)
                await emit_fn(self.session_id, SimEvent(
                    event_type="machine_alert",
                    virtual_time=end_time,
                    payload={
                        "machine_id": target_machine,
                        "failure_probability": prob,
                        "severity": _classify_severity(prob),
                        "message": f"Anomaly detected on machine {target_machine}.",
                    },
                ).to_dict())

        # Final event
        self._virtual_time = self.schedule[-1][4] if self.schedule else 0.0
        await emit_fn(self.session_id, SimEvent(
            event_type="sim_complete",
            virtual_time=self._virtual_time,
            payload={"message": "Digital twin simulation complete."},
        ).to_dict())
        self._running = False

    async def inject_disruption(self, disruption: dict) -> None:
        """Queue a disruption to be processed during the simulation."""
        await self._disruption_queue.put(disruption)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _advance_to(self, target_time: float, current_time: float, emit_fn) -> None:
        """Sleep for the real-time equivalent of advancing the virtual clock."""
        delta_virtual = max(0.0, target_time - current_time)
        delta_real = delta_virtual / self.speed_factor
        self._virtual_time = target_time

        # Check for any injected disruptions while sleeping
        if delta_real > 0.001:
            try:
                await asyncio.wait_for(self._process_disruptions(emit_fn), timeout=delta_real)
            except asyncio.TimeoutError:
                pass  # Normal — timeout means no disruption, just sleep expired

    async def _process_disruptions(self, emit_fn) -> None:
        """Process all pending disruptions from the queue."""
        while True:
            disruption = await self._disruption_queue.get()
            dtype = disruption.get("disruption_type", "")

            if dtype == "breakdown":
                machine_id = str(disruption.get("machine_id", ""))
                duration = float(disruption.get("duration", 20.0))
                at_time = float(disruption.get("at_time", self._virtual_time))
                self._breakdowns[machine_id] = at_time + duration
                await emit_fn(self.session_id, SimEvent(
                    event_type="breakdown",
                    virtual_time=self._virtual_time,
                    payload={
                        "machine_id": machine_id,
                        "duration": duration,
                        "message": f"Machine {machine_id} breakdown injected for {duration} time units.",
                    },
                ).to_dict())

            elif dtype == "rush_order":
                job_spec = disruption.get("rush_job", {})
                await emit_fn(self.session_id, SimEvent(
                    event_type="rush_order",
                    virtual_time=self._virtual_time,
                    payload={
                        "job": job_spec,
                        "message": f"Rush order injected: job {job_spec.get('job_id')}.",
                    },
                ).to_dict())


# ---------------------------------------------------------------------------
# Severity helper (duplicated here to avoid circular imports)
# ---------------------------------------------------------------------------

def _classify_severity(prob: float) -> str:
    if prob >= 0.80:
        return "critical"
    if prob >= 0.60:
        return "high"
    if prob >= 0.35:
        return "medium"
    return "low"
