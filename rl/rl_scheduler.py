"""
rl/rl_scheduler.py
RL-based schedule generator (Phase 4).

Thin adapter layer between the trained QAgent and the existing schedule
pipeline that expects a list of (job_id, op_index, machine_id, start, end) tuples.
"""
from __future__ import annotations

import os
from typing import List, Optional, Tuple

from models import Job, Machine
from rl.environment import ShopFloorEnv
from rl.q_agent import QAgent
from core.logger import logger

# Default path for the pre-trained model shipped with the project
_DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "rl_models")


def run_rl_schedule(
    jobs: List[Job],
    machines: List[Machine],
    setup_time: int = 2,
    model_path: Optional[str] = None,
    lambda_tardiness: float = 0.5,
) -> List[Tuple[int, int, int, float, float]]:
    """
    Generate a schedule using a trained Q-agent (greedy policy, ε=0).

    If `model_path` is None, attempts to load the latest model from
    `rl_models/`. Falls back to a short online training run if no saved
    model exists.

    Returns:
        List of (job_id, op_index, machine_id, start_time, end_time) tuples,
        compatible with the rest of the scheduling pipeline.
    """
    # Resolve model path
    if model_path is None:
        model_path = _find_latest_model()

    env = ShopFloorEnv(
        jobs=jobs,
        machines=machines,
        setup_time=setup_time,
        lambda_tardiness=lambda_tardiness,
    )

    if model_path and os.path.isfile(model_path):
        agent = QAgent.load(model_path)
        agent.epsilon = 0.0  # pure greedy inference
        logger.info(f"RL scheduler loaded model from {model_path}")
    else:
        # No pre-trained model → quick online training (50 episodes)
        logger.warning("No RL model found — running quick 50-episode training as fallback.")
        agent = QAgent(n_actions=len(jobs))
        agent.train(lambda: ShopFloorEnv(jobs, machines, setup_time, lambda_tardiness), episodes=50)
        agent.epsilon = 0.0

    obs = env.reset()
    done = False

    while not done:
        valid = [
            j for j in range(env.n_jobs)
            if env._op_pointer[j] < len(env._jobs[j].operations)
        ]
        if not valid:
            break
        action = agent.select_action(obs, valid_actions=valid)
        obs, _, done, _ = env.step(action)

    schedule = env.get_schedule()
    logger.info(f"RL scheduler produced {len(schedule)} operations, makespan={env._current_time:.1f}")
    return schedule


def _find_latest_model() -> Optional[str]:
    """Scan the rl_models/ directory and return the path of the newest JSON model."""
    if not os.path.isdir(_DEFAULT_MODEL_DIR):
        return None
    candidates = [
        os.path.join(_DEFAULT_MODEL_DIR, f)
        for f in os.listdir(_DEFAULT_MODEL_DIR)
        if f.endswith(".json")
    ]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)
