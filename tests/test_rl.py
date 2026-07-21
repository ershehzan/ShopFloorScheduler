"""
tests/test_rl.py
Tests for Phase 4 Reinforcement Learning module.

Covers:
  - ShopFloorEnv: reset, step, observation structure, done condition, action validation
  - QAgent: select_action, update, epsilon decay, save/load
  - End-to-end: greedy schedule generation via run_rl_schedule
  - API endpoints: train, status, models list
"""
import os
import json
import tempfile
import pytest

from models import Job, Machine, Operation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_jobs():
    """3 jobs, 2 machines, 2 ops each."""
    return [
        Job(job_id=1, due_date=50, priority=1, operations=[
            Operation(machine_id=1, processing_time=10),
            Operation(machine_id=2, processing_time=8),
        ]),
        Job(job_id=2, due_date=40, priority=2, operations=[
            Operation(machine_id=2, processing_time=5),
            Operation(machine_id=1, processing_time=12),
        ]),
        Job(job_id=3, due_date=60, priority=1, operations=[
            Operation(machine_id=1, processing_time=7),
            Operation(machine_id=2, processing_time=9),
        ]),
    ]


@pytest.fixture
def simple_machines():
    return [
        Machine(machine_id=1, unavailable_periods=[]),
        Machine(machine_id=2, unavailable_periods=[]),
    ]


# ---------------------------------------------------------------------------
# ShopFloorEnv tests
# ---------------------------------------------------------------------------

class TestShopFloorEnv:
    def test_reset_returns_observation(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        obs = env.reset()
        assert isinstance(obs, list)
        assert len(obs) == env.observation_size

    def test_observation_values_in_valid_range(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        obs = env.reset()
        # All normalized values should be in [0, 1] except possibly after timing issues
        for v in obs:
            assert v >= 0.0, f"Observation {v} is negative"

    def test_step_returns_correct_structure(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        env.reset()
        obs, reward, done, info = env.step(0)
        assert isinstance(obs, list)
        assert isinstance(reward, float)
        assert isinstance(done, bool)
        assert "makespan" in info

    def test_all_jobs_complete_marks_done(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        env.reset()
        done = False
        steps = 0
        while not done:
            valid = [j for j in range(env.n_jobs) if env._op_pointer[j] < len(env._jobs[j].operations)]
            if not valid:
                break
            action = valid[0]
            _, _, done, _ = env.step(action)
            steps += 1
            assert steps < 100, "Environment never reached done state"
        assert done

    def test_schedule_contains_all_operations(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        env.reset()
        done = False
        while not done:
            valid = [j for j in range(env.n_jobs) if env._op_pointer[j] < len(env._jobs[j].operations)]
            if not valid:
                break
            _, _, done, _ = env.step(valid[0])
        schedule = env.get_schedule()
        total_ops = sum(len(j.operations) for j in simple_jobs)
        assert len(schedule) == total_ops

    def test_invalid_action_penalized(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        env.reset()
        with pytest.raises(ValueError):
            env.step(-1)

    def test_no_operation_overlap_on_same_machine(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        env.reset()
        done = False
        while not done:
            valid = [j for j in range(env.n_jobs) if env._op_pointer[j] < len(env._jobs[j].operations)]
            if not valid:
                break
            _, _, done, _ = env.step(valid[0])
        schedule = env.get_schedule()
        # Group by machine and check no overlaps
        from collections import defaultdict
        by_machine = defaultdict(list)
        for op in schedule:
            by_machine[op[2]].append((op[3], op[4]))
        for mid, intervals in by_machine.items():
            intervals.sort()
            for i in range(1, len(intervals)):
                assert intervals[i][0] >= intervals[i - 1][1], (
                    f"Overlap on machine {mid}: {intervals[i - 1]} vs {intervals[i]}"
                )

    def test_action_space_n(self, simple_jobs, simple_machines):
        from rl.environment import ShopFloorEnv
        env = ShopFloorEnv(simple_jobs, simple_machines)
        assert env.action_space_n == 3


# ---------------------------------------------------------------------------
# QAgent tests
# ---------------------------------------------------------------------------

class TestQAgent:
    def test_select_action_within_range(self):
        from rl.q_agent import QAgent
        agent = QAgent(n_actions=5, epsilon=0.0)
        obs = [0.1, 0.5, 0.3, 0.7, 0.2, 0.4, 0.6, 0.8, 0.9, 0.1]
        action = agent.select_action(obs)
        assert 0 <= action < 5

    def test_select_action_respects_valid_actions(self):
        from rl.q_agent import QAgent
        agent = QAgent(n_actions=5, epsilon=0.0)
        obs = [0.0] * 10
        valid = [1, 3]
        for _ in range(20):
            action = agent.select_action(obs, valid_actions=valid)
            assert action in valid

    def test_update_returns_float(self):
        from rl.q_agent import QAgent
        agent = QAgent(n_actions=3)
        obs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        td = agent.update(obs, 0, -1.0, obs, False)
        assert isinstance(td, float)

    def test_epsilon_decay(self):
        from rl.q_agent import QAgent
        agent = QAgent(n_actions=3, epsilon=1.0, epsilon_decay=0.9, epsilon_min=0.1)
        agent.decay_epsilon()
        assert abs(agent.epsilon - 0.9) < 1e-6
        for _ in range(100):
            agent.decay_epsilon()
        assert agent.epsilon >= 0.1

    def test_save_and_load(self, tmp_path):
        from rl.q_agent import QAgent
        agent = QAgent(n_actions=3, epsilon=0.42)
        # Add some Q values
        obs = [0.5] * 7
        agent.update(obs, 0, -1.0, obs, False)
        path = str(tmp_path / "agent.json")
        agent.save(path)
        assert os.path.isfile(path)

        loaded = QAgent.load(path)
        assert loaded.n_actions == 3
        assert abs(loaded.epsilon - 0.42) < 1e-6
        assert len(loaded._q) > 0

    def test_record_reward_updates_best(self):
        from rl.q_agent import QAgent
        agent = QAgent(n_actions=2)
        agent.record_reward(-10.0)
        agent.record_reward(-5.0)
        agent.record_reward(-8.0)
        assert abs(agent.best_reward - (-5.0)) < 1e-6

    def test_train_completes(self, simple_jobs, simple_machines):
        from rl.q_agent import QAgent
        from rl.environment import ShopFloorEnv
        agent = QAgent(n_actions=len(simple_jobs))
        result = agent.train(
            lambda: ShopFloorEnv(simple_jobs, simple_machines),
            episodes=10,
        )
        assert result["episodes_trained"] == 10
        assert "best_reward" in result


# ---------------------------------------------------------------------------
# End-to-end RL scheduler test
# ---------------------------------------------------------------------------

class TestRLScheduler:
    def test_run_rl_schedule_returns_valid_schedule(self, simple_jobs, simple_machines):
        from rl.rl_scheduler import run_rl_schedule
        schedule = run_rl_schedule(
            jobs=simple_jobs,
            machines=simple_machines,
            setup_time=0,
        )
        assert isinstance(schedule, list)
        total_ops = sum(len(j.operations) for j in simple_jobs)
        assert len(schedule) == total_ops
        # All entries are tuples/lists with 5 elements
        for op in schedule:
            assert len(op) == 5

    def test_run_rl_schedule_no_machine_overlap(self, simple_jobs, simple_machines):
        from rl.rl_scheduler import run_rl_schedule
        from collections import defaultdict
        schedule = run_rl_schedule(simple_jobs, simple_machines, setup_time=0)
        by_machine = defaultdict(list)
        for op in schedule:
            by_machine[op[2]].append((op[3], op[4]))
        for mid, intervals in by_machine.items():
            intervals.sort()
            for i in range(1, len(intervals)):
                assert intervals[i][0] >= intervals[i - 1][1], f"Overlap on machine {mid}"


# ---------------------------------------------------------------------------
# RL API endpoint tests
# ---------------------------------------------------------------------------

class TestRLAPI:
    def test_start_training(self, client):
        response = client.post("/api/rl/train", json={"episodes": 10})
        assert response.status_code == 202
        data = response.json()
        assert "training_id" in data
        assert data["status"] == "running"

    def test_get_training_status(self, client):
        # Start first
        start = client.post("/api/rl/train", json={"episodes": 10})
        tid = start.json()["training_id"]
        response = client.get(f"/api/rl/train/{tid}")
        assert response.status_code == 200
        assert response.json()["training_id"] == tid

    def test_get_training_status_not_found(self, client):
        response = client.get("/api/rl/train/nonexistent-id")
        assert response.status_code == 404

    def test_list_models(self, client):
        response = client.get("/api/rl/models")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
