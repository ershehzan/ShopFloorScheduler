"""
rl/q_agent.py
Tabular Q-learning agent for shop floor scheduling (Phase 4).

Design choices:
  - State is discretized into a hash-based key (tuple of quantized observation bins).
  - Q-table is a plain Python dict mapping (state_key, action) → q_value.
  - Experience replay buffer retains recent transitions and samples mini-batches
    for more stable updates.
  - Agent supports save/load to JSON for persistence.
"""
from __future__ import annotations

import json
import math
import os
import random
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from core.logger import logger


# ---------------------------------------------------------------------------
# Experience replay buffer
# ---------------------------------------------------------------------------

class ReplayBuffer:
    """Fixed-size circular buffer for experience replay."""

    def __init__(self, capacity: int = 2000) -> None:
        self._buf: Deque[tuple] = deque(maxlen=capacity)

    def push(self, state_key: str, action: int, reward: float, next_key: str, done: bool) -> None:
        self._buf.append((state_key, action, reward, next_key, done))

    def sample(self, batch_size: int) -> List[tuple]:
        return random.sample(self._buf, min(batch_size, len(self._buf)))

    def __len__(self) -> int:
        return len(self._buf)


# ---------------------------------------------------------------------------
# Q-Agent
# ---------------------------------------------------------------------------

class QAgent:
    """
    Tabular Q-learning agent with ε-greedy exploration and experience replay.

    The Q-table maps ``(state_key, action_index)`` pairs to Q-values.  State
    keys are produced by discretizing the continuous observation vector into
    bins and hashing the resulting tuple — this avoids the curse of
    dimensionality for small problems while remaining dependency-free.
    """

    def __init__(
        self,
        n_actions: int,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.05,
        n_bins: int = 8,
        replay_capacity: int = 2000,
        batch_size: int = 32,
    ) -> None:
        self.n_actions = n_actions
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.n_bins = n_bins
        self.batch_size = batch_size

        self._q: Dict[Tuple[str, int], float] = {}
        self._replay = ReplayBuffer(capacity=replay_capacity)

        # Training history
        self.reward_history: List[float] = []
        self.best_reward: float = -math.inf

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_action(self, obs: List[float], valid_actions: Optional[List[int]] = None) -> int:
        """
        ε-greedy action selection.

        Args:
            obs:           Current observation vector.
            valid_actions: Subset of legal actions (defaults to all actions).
        """
        if valid_actions is None:
            valid_actions = list(range(self.n_actions))

        if random.random() < self.epsilon:
            return random.choice(valid_actions)

        state_key = self._discretize(obs)
        q_vals = {a: self._q.get((state_key, a), 0.0) for a in valid_actions}
        return max(q_vals, key=q_vals.__getitem__)

    def update(
        self,
        obs: List[float],
        action: int,
        reward: float,
        next_obs: List[float],
        done: bool,
    ) -> float:
        """
        Store transition in replay buffer and perform a batch Q-update.

        Returns:
            The TD error of the direct (non-batch) update for logging.
        """
        state_key = self._discretize(obs)
        next_key = self._discretize(next_obs)

        self._replay.push(state_key, action, reward, next_key, done)

        # Direct update on the current transition
        td_error = self._td_update(state_key, action, reward, next_key, done)

        # Batch update from replay buffer
        if len(self._replay) >= self.batch_size:
            for s_k, a, r, ns_k, d in self._replay.sample(self.batch_size):
                self._td_update(s_k, a, r, ns_k, d)

        return td_error

    def decay_epsilon(self) -> None:
        """Apply epsilon decay at the end of each episode."""
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def record_reward(self, episode_reward: float) -> None:
        """Record the total reward for a completed episode."""
        self.reward_history.append(episode_reward)
        if episode_reward > self.best_reward:
            self.best_reward = episode_reward

    def save(self, path: str) -> None:
        """Serialize the Q-table and metadata to a JSON file."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        payload: Dict[str, Any] = {
            "n_actions": self.n_actions,
            "learning_rate": self.lr,
            "discount_factor": self.gamma,
            "epsilon": self.epsilon,
            "epsilon_decay": self.epsilon_decay,
            "epsilon_min": self.epsilon_min,
            "n_bins": self.n_bins,
            "best_reward": self.best_reward,
            "episodes_trained": len(self.reward_history),
            # Serialize Q-table: keys are "state_key|action" strings
            "q_table": {
                f"{s}|{a}": v for (s, a), v in self._q.items()
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        logger.info(f"QAgent saved to {path} ({len(self._q)} Q-entries, ε={self.epsilon:.4f})")

    @classmethod
    def load(cls, path: str) -> "QAgent":
        """Reconstruct a QAgent from a saved JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        agent = cls(
            n_actions=payload["n_actions"],
            learning_rate=payload["learning_rate"],
            discount_factor=payload["discount_factor"],
            epsilon=payload["epsilon"],
            epsilon_decay=payload["epsilon_decay"],
            epsilon_min=payload["epsilon_min"],
            n_bins=payload["n_bins"],
        )
        agent.best_reward = payload["best_reward"]
        agent._q = {}
        for key_str, val in payload["q_table"].items():
            s_key, a_str = key_str.rsplit("|", 1)
            agent._q[(s_key, int(a_str))] = float(val)

        logger.info(f"QAgent loaded from {path} ({len(agent._q)} Q-entries)")
        return agent

    # ------------------------------------------------------------------
    # Training loop (standalone — also invoked by the API endpoint)
    # ------------------------------------------------------------------

    def train(
        self,
        env_factory,  # Callable[[], ShopFloorEnv]
        episodes: int = 500,
        progress_callback=None,  # Callable[[int, float, float], None]
    ) -> Dict[str, Any]:
        """
        Run the Q-learning training loop.

        Args:
            env_factory:       Zero-argument factory that returns a fresh env per episode.
            episodes:          Number of episodes to train.
            progress_callback: Optional fn(episode, reward, epsilon) called every 50 episodes.

        Returns:
            Dict with training summary statistics.
        """
        for ep in range(1, episodes + 1):
            env = env_factory()
            obs = env.reset()
            ep_reward = 0.0
            done = False
            steps = 0

            while not done:
                # Compute valid actions: jobs that still have remaining ops
                valid = [
                    j for j in range(env.n_jobs)
                    if env._op_pointer[j] < len(env._jobs[j].operations)
                ]
                if not valid:
                    break
                action = self.select_action(obs, valid_actions=valid)
                next_obs, reward, done, _ = env.step(action)
                self.update(obs, action, reward, next_obs, done)
                obs = next_obs
                ep_reward += reward
                steps += 1

            self.decay_epsilon()
            self.record_reward(ep_reward)

            if progress_callback and ep % 50 == 0:
                progress_callback(ep, ep_reward, self.epsilon)
            if ep % 100 == 0:
                logger.info(
                    f"RL Training ep={ep}/{episodes} reward={ep_reward:.3f} "
                    f"best={self.best_reward:.3f} ε={self.epsilon:.4f}"
                )

        return {
            "episodes_trained": episodes,
            "best_reward": self.best_reward,
            "final_epsilon": self.epsilon,
            "q_table_size": len(self._q),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _td_update(
        self,
        state_key: str,
        action: int,
        reward: float,
        next_key: str,
        done: bool,
    ) -> float:
        current_q = self._q.get((state_key, action), 0.0)
        if done:
            target = reward
        else:
            next_q_vals = [self._q.get((next_key, a), 0.0) for a in range(self.n_actions)]
            target = reward + self.gamma * max(next_q_vals)
        td_error = target - current_q
        self._q[(state_key, action)] = current_q + self.lr * td_error
        return td_error

    def _discretize(self, obs: List[float]) -> str:
        """
        Bin each observation dimension into `n_bins` equal-width buckets in [0, 1]
        and return a comma-joined string as the state key.
        """
        bins = []
        for v in obs:
            # Clamp to [0, 1] then bin
            clamped = max(0.0, min(1.0, v))
            b = min(int(clamped * self.n_bins), self.n_bins - 1)
            bins.append(str(b))
        return ",".join(bins)
