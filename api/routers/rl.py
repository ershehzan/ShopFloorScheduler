"""
api/routers/rl.py
Reinforcement Learning training and model management endpoints (Phase 4).

Routes:
  POST   /api/rl/train                    — Start background RL training run
  GET    /api/rl/train/{training_id}      — Poll training status
  GET    /api/rl/models                   — List saved model snapshots
  DELETE /api/rl/models/{model_id}        — Delete a saved model
"""
from __future__ import annotations

import datetime
import json
import os
import threading
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException

from api.schemas import RLTrainRequest, RLTrainStatusOut, RLModelOut
from core.logger import logger

router = APIRouter(prefix="/api/rl", tags=["reinforcement-learning"])

# ---------------------------------------------------------------------------
# In-process training registry (survives only for server lifetime)
# ---------------------------------------------------------------------------

_TRAINING_REGISTRY: Dict[str, Dict[str, Any]] = {}
_RL_MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "rl_models")


def _ensure_models_dir() -> str:
    os.makedirs(_RL_MODELS_DIR, exist_ok=True)
    return _RL_MODELS_DIR


# ---------------------------------------------------------------------------
# POST /api/rl/train
# ---------------------------------------------------------------------------

@router.post("/train", response_model=RLTrainStatusOut, status_code=202)
def start_training(payload: RLTrainRequest, background_tasks: BackgroundTasks):
    """
    Start an RL training run in a background thread.

    Training uses synthetic job/machine data so no upload is required.
    Returns a `training_id` to poll for status.
    """
    training_id = str(uuid.uuid4())
    _TRAINING_REGISTRY[training_id] = {
        "status": "running",
        "episodes_done": 0,
        "total_episodes": payload.episodes,
        "current_reward": None,
        "best_reward": None,
        "message": "Training started.",
        "model_path": None,
        "model_name": payload.model_name,
        "started_at": datetime.datetime.utcnow().isoformat(),
    }
    background_tasks.add_task(_run_training, training_id, payload)
    logger.info(f"RL training started: id={training_id} episodes={payload.episodes}")
    return _reg_to_schema(training_id)


# ---------------------------------------------------------------------------
# GET /api/rl/train/{training_id}
# ---------------------------------------------------------------------------

@router.get("/train/{training_id}", response_model=RLTrainStatusOut)
def get_training_status(training_id: str):
    """Poll the status of a background RL training run."""
    if training_id not in _TRAINING_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Training run '{training_id}' not found.")
    return _reg_to_schema(training_id)


# ---------------------------------------------------------------------------
# GET /api/rl/models
# ---------------------------------------------------------------------------

@router.get("/models", response_model=List[RLModelOut])
def list_models():
    """List all saved RL model snapshots."""
    models_dir = _ensure_models_dir()
    result: List[RLModelOut] = []
    for fname in sorted(os.listdir(models_dir), reverse=True):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(models_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                meta = json.load(f)
            model_id = fname.replace(".json", "")
            result.append(RLModelOut(
                model_id=model_id,
                model_name=meta.get("model_name"),
                created_at=meta.get("saved_at", ""),
                episodes_trained=meta.get("episodes_trained", 0),
                best_reward=meta.get("best_reward"),
                file_path=fpath,
            ))
        except Exception as exc:
            logger.warning(f"Could not read RL model {fpath}: {exc}")
    return result


# ---------------------------------------------------------------------------
# DELETE /api/rl/models/{model_id}
# ---------------------------------------------------------------------------

@router.delete("/models/{model_id}", status_code=204)
def delete_model(model_id: str):
    """Delete a saved RL model file."""
    models_dir = _ensure_models_dir()
    fpath = os.path.join(models_dir, f"{model_id}.json")
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")
    os.remove(fpath)
    logger.info(f"Deleted RL model: {model_id}")


# ---------------------------------------------------------------------------
# Background training worker
# ---------------------------------------------------------------------------

def _run_training(training_id: str, payload: RLTrainRequest) -> None:
    """Background thread: run RL training, save model, update registry."""
    try:
        from rl.q_agent import QAgent
        from rl.environment import ShopFloorEnv
        from models import Job, Machine, Operation

        # Build synthetic training data (3 machines, 5 jobs)
        machines = [Machine(machine_id=i, unavailable_periods=[]) for i in range(1, 4)]
        import random
        rng = random.Random(42)
        jobs = []
        for j in range(1, 6):
            ops = [
                Operation(machine_id=rng.randint(1, 3), processing_time=rng.randint(5, 20))
                for _ in range(rng.randint(2, 4))
            ]
            jobs.append(Job(
                job_id=j,
                operations=ops,
                due_date=rng.randint(40, 120),
                priority=rng.randint(1, 5),
            ))

        agent = QAgent(
            n_actions=len(jobs),
            learning_rate=payload.learning_rate,
            discount_factor=payload.discount_factor,
            epsilon=payload.epsilon,
            epsilon_decay=payload.epsilon_decay,
            epsilon_min=payload.epsilon_min,
        )

        reg = _TRAINING_REGISTRY[training_id]

        def _progress(ep: int, reward: float, epsilon: float) -> None:
            reg["episodes_done"] = ep
            reg["current_reward"] = round(reward, 4)
            reg["best_reward"] = round(agent.best_reward, 4)

        agent.train(
            env_factory=lambda: ShopFloorEnv(
                jobs=jobs,
                machines=machines,
                setup_time=2,
                lambda_tardiness=payload.lambda_tardiness,
            ),
            episodes=payload.episodes,
            progress_callback=_progress,
        )

        # Save model
        models_dir = _ensure_models_dir()
        model_id = training_id[:8]
        model_path = os.path.join(models_dir, f"{model_id}.json")
        agent.save(model_path)

        # Patch the saved JSON with extra metadata
        with open(model_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        saved["model_name"] = payload.model_name or f"model_{model_id}"
        saved["saved_at"] = datetime.datetime.utcnow().isoformat()
        with open(model_path, "w", encoding="utf-8") as f:
            json.dump(saved, f)

        reg.update({
            "status": "complete",
            "episodes_done": payload.episodes,
            "current_reward": round(agent.reward_history[-1] if agent.reward_history else 0.0, 4),
            "best_reward": round(agent.best_reward, 4),
            "message": "Training complete. Model saved.",
            "model_path": model_path,
        })
        logger.info(f"RL training complete: id={training_id} best_reward={agent.best_reward:.4f}")

    except Exception as exc:
        logger.exception(f"RL training error for {training_id}: {exc}")
        _TRAINING_REGISTRY[training_id].update({
            "status": "error",
            "message": str(exc),
        })


# ---------------------------------------------------------------------------
# Registry to schema helper
# ---------------------------------------------------------------------------

def _reg_to_schema(training_id: str) -> RLTrainStatusOut:
    r = _TRAINING_REGISTRY[training_id]
    return RLTrainStatusOut(
        training_id=training_id,
        status=r["status"],
        episodes_done=r["episodes_done"],
        total_episodes=r["total_episodes"],
        current_reward=r["current_reward"],
        best_reward=r["best_reward"],
        message=r["message"],
        model_path=r.get("model_path"),
    )
