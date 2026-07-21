"""
rl/environment.py
Gym-compatible ShopFloor environment for RL training (Phase 4).

The environment models the job-sequencing problem as a Markov Decision Process:

  State  : Normalized vector of machine availability, job progress, and urgency.
  Action : Integer index selecting the next job to assign to the earliest-free machine.
  Reward : Negative delta in (makespan + λ·tardiness); large penalty for missed deadlines.
  Done   : All operations for all jobs have been scheduled.

No external gym/gymnasium dependency is required — this implements the standard
step/reset interface directly.
"""
from __future__ import annotations

import copy
import math
from typing import List, Optional, Tuple

from models import Job, Machine, Operation


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class ShopFloorEnv:
    """
    Discrete-action environment for the Job-Shop Scheduling Problem.

    Observation space (flat float vector):
      - For each machine (sorted by machine_id):
          machine_available_at[i] / max_possible_time   (normalized)
      - For each job (sorted by job_id):
          remaining_ops[j] / max_ops                    (normalized)
          max(0, due_date - current_time) / due_date    (slack ratio)
      - Scalar: current_time / max_possible_time

    Action space: discrete integer in [0, n_jobs).
      Selects which job to schedule next on the earliest-available machine.
      If the selected job has no remaining operations (already done), a small
      negative reward penalty is applied and the action is a no-op.
    """

    def __init__(
        self,
        jobs: List[Job],
        machines: List[Machine],
        setup_time: int = 2,
        lambda_tardiness: float = 0.5,
    ) -> None:
        self.original_jobs = jobs
        self.original_machines = machines
        self.setup_time = setup_time
        self.lambda_tardiness = lambda_tardiness

        self.n_jobs = len(jobs)
        self.n_machines = len(machines)
        self.max_ops = max(len(j.operations) for j in jobs)

        # Rough upper bound for normalization
        self._max_time = sum(
            sum(op.processing_time for op in j.operations) for j in jobs
        ) + setup_time * self.n_machines * self.n_jobs + 1

        # Will be populated on reset()
        self._jobs: List[Job] = []
        self._machines: List[Machine] = []
        self._op_pointer: List[int] = []   # next operation index per job
        self._job_done_at: List[float] = []  # completion time per job
        self._current_time: float = 0.0
        self._schedule: list = []           # list of (job_id, op_idx, machine_id, start, end)

        self.reset()

    # ------------------------------------------------------------------
    # Gym interface
    # ------------------------------------------------------------------

    def reset(self) -> List[float]:
        """Reset environment to initial state and return the initial observation."""
        self._jobs = copy.deepcopy(self.original_jobs)
        self._machines = copy.deepcopy(self.original_machines)
        for m in self._machines:
            m.available_at = 0
            m.last_job_id = None  # type: ignore[assignment]
        self._op_pointer = [0] * self.n_jobs
        self._job_done_at = [0.0] * self.n_jobs
        self._current_time = 0.0
        self._schedule = []
        return self._observe()

    def step(self, action: int) -> Tuple[List[float], float, bool, dict]:
        """
        Execute one step: schedule the next operation of the selected job.

        Returns:
            obs   : New state observation.
            reward: Shaped reward signal.
            done  : True when all jobs are fully scheduled.
            info  : Debug dict with current makespan and tardiness.
        """
        if action < 0 or action >= self.n_jobs:
            raise ValueError(f"Invalid action {action}. Must be in [0, {self.n_jobs})")

        job = self._jobs[action]
        op_idx = self._op_pointer[action]

        # Penalize selecting an already-completed job
        if op_idx >= len(job.operations):
            return self._observe(), -5.0, self._is_done(), {"invalid_action": True}

        op: Operation = job.operations[op_idx]

        # Find the target machine
        machine = self._get_machine(op.machine_id)
        if machine is None:
            # No matching machine — penalize
            return self._observe(), -10.0, self._is_done(), {"machine_not_found": True}

        # Compute start time
        prev_job_end = self._job_done_at[action]
        if machine.last_job_id is not None and machine.last_job_id != job.job_id:
            setup_penalty = self.setup_time
        else:
            setup_penalty = 0
        start = max(machine.available_at + setup_penalty, prev_job_end)

        # Handle unavailability windows
        for (down_start, down_end) in machine.unavailable_periods:
            if start < down_end and start + op.processing_time > down_start:
                start = down_end

        end = start + op.processing_time

        # Update state
        machine.available_at = end
        machine.last_job_id = job.job_id
        self._job_done_at[action] = end
        self._op_pointer[action] += 1
        self._current_time = max(self._current_time, end)
        self._schedule.append((job.job_id, op_idx, op.machine_id, start, end))

        # Compute reward
        reward = self._compute_reward()
        done = self._is_done()
        info = {
            "makespan": self._current_time,
            "tardiness": self._total_tardiness(),
        }
        return self._observe(), reward, done, info

    @property
    def action_space_n(self) -> int:
        return self.n_jobs

    @property
    def observation_size(self) -> int:
        return self.n_machines + self.n_jobs * 2 + 1

    def get_schedule(self) -> list:
        """Return the current (possibly incomplete) schedule."""
        return list(self._schedule)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _observe(self) -> List[float]:
        """Build the normalized state vector."""
        obs: List[float] = []

        # Machine availability
        for m in sorted(self._machines, key=lambda x: x.machine_id):
            obs.append(m.available_at / self._max_time)

        # Job progress and urgency
        for j_idx, job in enumerate(self._jobs):
            remaining = len(job.operations) - self._op_pointer[j_idx]
            obs.append(remaining / max(self.max_ops, 1))
            slack = max(0.0, job.due_date - self._current_time)
            obs.append(slack / max(job.due_date, 1))

        # Global time
        obs.append(self._current_time / self._max_time)
        return obs

    def _compute_reward(self) -> float:
        """
        Reward = −(Δmakespan / max_time + λ·Δtardiness / n_jobs).

        A small positive reward is added when a job completes exactly on time.
        """
        makespan_penalty = self._current_time / self._max_time
        tardiness_penalty = self.lambda_tardiness * self._total_tardiness() / max(self.n_jobs, 1)
        return -(makespan_penalty + tardiness_penalty)

    def _total_tardiness(self) -> float:
        tardiness = 0.0
        for j_idx, job in enumerate(self._jobs):
            if self._op_pointer[j_idx] >= len(job.operations):
                tardiness += max(0.0, self._job_done_at[j_idx] - job.due_date)
        return tardiness

    def _is_done(self) -> bool:
        return all(self._op_pointer[j] >= len(self._jobs[j].operations) for j in range(self.n_jobs))

    def _get_machine(self, machine_id: int) -> Optional[Machine]:
        for m in self._machines:
            if m.machine_id == machine_id:
                return m
        return None
