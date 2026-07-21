"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { BrainCircuit, Play, Trash2, RefreshCw, TrendingDown, Award, ChevronRight } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

interface RLTrainStatus {
  training_id: string;
  status: "running" | "complete" | "error";
  episodes_done: number;
  total_episodes: number;
  current_reward?: number;
  best_reward?: number;
  message: string;
  model_path?: string;
}

interface RLModel {
  model_id: string;
  model_name?: string;
  created_at: string;
  episodes_trained: number;
  best_reward?: number;
  file_path: string;
}

// ─── Mini reward chart ────────────────────────────────────────────────────────

function RewardChart({ rewards }: { rewards: number[] }) {
  if (rewards.length < 2) {
    return (
      <div style={{
        height: 120, display: "flex", alignItems: "center", justifyContent: "center",
        color: "var(--text-muted)", fontSize: "0.875rem",
      }}>
        Waiting for training to start…
      </div>
    );
  }
  const max = Math.max(...rewards);
  const min = Math.min(...rewards);
  const range = max - min || 1;
  const w = 600, h = 120;
  const pts = rewards.map((v, i) => {
    const x = (i / (rewards.length - 1)) * (w - 20) + 10;
    const y = h - 10 - ((v - min) / range) * (h - 20);
    return `${x},${y}`;
  });
  const area = `${pts.join(" ")} ${w - 10},${h - 10} 10,${h - 10}`;

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: "block" }}>
      <defs>
        <linearGradient id="rlRewardGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={area} fill="url(#rlRewardGrad)" />
      <polyline points={pts.join(" ")} fill="none" stroke="#8b5cf6" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
      <circle
        cx={pts[pts.length - 1].split(",")[0]}
        cy={pts[pts.length - 1].split(",")[1]}
        r={5} fill="#8b5cf6"
      />
    </svg>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function RLOptimizerPage() {
  const [episodes, setEpisodes] = useState(500);
  const [learningRate, setLearningRate] = useState(0.1);
  const [lambdaTardiness, setLambdaTardiness] = useState(0.5);
  const [modelName, setModelName] = useState("");
  const [training, setTraining] = useState<RLTrainStatus | null>(null);
  const [models, setModels] = useState<RLModel[]>([]);
  const [rewardHistory, setRewardHistory] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const fetchModels = useCallback(async () => {
    const res = await fetch(`${API_BASE}/api/rl/models`);
    if (res.ok) setModels(await res.json());
  }, []);

  const pollTraining = useCallback(async (trainingId: string) => {
    const res = await fetch(`${API_BASE}/api/rl/train/${trainingId}`);
    if (!res.ok) return;
    const data: RLTrainStatus = await res.json();
    setTraining(data);

    // Track reward history
    if (data.current_reward != null) {
      setRewardHistory((prev) => [...prev, data.current_reward!]);
    }

    if (data.status === "running") {
      pollRef.current = setTimeout(() => pollTraining(trainingId), 800);
    } else {
      fetchModels();
    }
  }, [fetchModels]);

  const handleStartTraining = async () => {
    if (pollRef.current) clearTimeout(pollRef.current);
    setLoading(true);
    setRewardHistory([]);
    setTraining(null);
    try {
      const res = await fetch(`${API_BASE}/api/rl/train`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          episodes,
          learning_rate: learningRate,
          lambda_tardiness: lambdaTardiness,
          model_name: modelName || undefined,
        }),
      });
      if (res.ok) {
        const data: RLTrainStatus = await res.json();
        setTraining(data);
        pollTraining(data.training_id);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteModel = async (modelId: string) => {
    await fetch(`${API_BASE}/api/rl/models/${modelId}`, { method: "DELETE" });
    fetchModels();
  };

  useEffect(() => {
    fetchModels();
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [fetchModels]);

  const progressPct = training
    ? Math.round((training.episodes_done / training.total_episodes) * 100)
    : 0;

  return (
    <div style={{ padding: "32px", maxWidth: 1200, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10,
            background: "linear-gradient(135deg, #8b5cf6, #ec4899)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <BrainCircuit size={20} color="#fff" />
          </div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            RL Optimizer
          </h1>
        </div>
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.9375rem" }}>
          Train a Q-learning agent to solve the job-shop scheduling problem through reinforcement learning
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "380px 1fr", gap: 24 }}>
        {/* Training config */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 20, color: "var(--text-primary)" }}>
              Training Configuration
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Episodes: <span style={{ color: "var(--accent)" }}>{episodes}</span>
                </label>
                <input
                  id="rl-episodes"
                  type="range" min={10} max={2000} step={10}
                  value={episodes}
                  onChange={(e) => setEpisodes(Number(e.target.value))}
                  style={{ width: "100%" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  <span>10</span><span>2000</span>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Learning Rate (α): <span style={{ color: "var(--accent)" }}>{learningRate}</span>
                </label>
                <input
                  id="rl-lr"
                  type="range" min={0.001} max={1.0} step={0.001}
                  value={learningRate}
                  onChange={(e) => setLearningRate(Number(Number(e.target.value).toFixed(3)))}
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Tardiness Weight (λ): <span style={{ color: "var(--accent)" }}>{lambdaTardiness}</span>
                </label>
                <input
                  id="rl-lambda"
                  type="range" min={0} max={5} step={0.1}
                  value={lambdaTardiness}
                  onChange={(e) => setLambdaTardiness(Number(e.target.value))}
                  style={{ width: "100%" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  <span>Makespan-focused</span><span>Tardiness-focused</span>
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Model Name (optional)
                </label>
                <input
                  id="rl-model-name"
                  type="text"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  placeholder="e.g. production-v1"
                  className="form-input"
                  style={{ width: "100%" }}
                />
              </div>

              <button
                id="btn-start-rl-training"
                onClick={handleStartTraining}
                disabled={loading || training?.status === "running"}
                className="btn btn-primary"
                style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
              >
                <Play size={16} />
                {training?.status === "running" ? "Training…" : "Start Training"}
              </button>
            </div>
          </div>

          {/* Info card */}
          <div className="card" style={{ padding: "20px 24px", background: "rgba(139,92,246,0.06)", border: "1px solid rgba(139,92,246,0.2)" }}>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.7 }}>
              <strong style={{ color: "var(--text-primary)" }}>How it works:</strong>
              <br />
              The Q-learning agent explores job sequencing decisions across training episodes, learning a policy that minimizes makespan + weighted tardiness.
              Once trained, the model can be selected as the <code style={{ fontSize: "0.75rem", background: "rgba(139,92,246,0.1)", padding: "1px 5px", borderRadius: 4 }}>RL</code> algorithm in the Schedule upload form.
            </div>
          </div>
        </div>

        {/* Training status + models */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Training progress */}
          <div className="card" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                Training Progress
              </h2>
              {training && (
                <span style={{
                  padding: "4px 12px", borderRadius: 99, fontSize: "0.75rem", fontWeight: 600,
                  color: training.status === "complete" ? "#22c55e" : training.status === "error" ? "#ef4444" : "#8b5cf6",
                  background: training.status === "complete" ? "rgba(34,197,94,0.1)" : training.status === "error" ? "rgba(239,68,68,0.1)" : "rgba(139,92,246,0.1)",
                }}>
                  {training.status.toUpperCase()}
                </span>
              )}
            </div>

            {training ? (
              <>
                {/* Progress bar */}
                <div style={{ marginBottom: 20 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem", color: "var(--text-muted)", marginBottom: 8 }}>
                    <span>Episode {training.episodes_done.toLocaleString()} / {training.total_episodes.toLocaleString()}</span>
                    <span>{progressPct}%</span>
                  </div>
                  <div style={{ height: 6, borderRadius: 99, background: "var(--border)", overflow: "hidden" }}>
                    <div style={{
                      height: "100%", borderRadius: 99,
                      background: "linear-gradient(90deg, #8b5cf6, #ec4899)",
                      width: `${progressPct}%`,
                      transition: "width 0.4s ease",
                    }} />
                  </div>
                </div>

                {/* Stats row */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
                  {[
                    { label: "Current Reward", value: training.current_reward?.toFixed(4) ?? "—", icon: TrendingDown, color: "#8b5cf6" },
                    { label: "Best Reward", value: training.best_reward?.toFixed(4) ?? "—", icon: Award, color: "#22c55e" },
                  ].map(({ label, value, icon: Icon, color }) => (
                    <div key={label} style={{ padding: "14px 16px", borderRadius: "var(--radius-md)", background: "var(--surface-elevated)", border: "1px solid var(--border)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                        <Icon size={14} color={color} />
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 500 }}>{label}</span>
                      </div>
                      <div style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
                    </div>
                  ))}
                </div>

                {/* Reward chart */}
                <div style={{ borderRadius: "var(--radius-md)", overflow: "hidden", background: "var(--surface-elevated)", border: "1px solid var(--border)", padding: "12px 8px" }}>
                  <RewardChart rewards={rewardHistory} />
                </div>

                {training.message && (
                  <div style={{ marginTop: 12, fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                    {training.message}
                  </div>
                )}
              </>
            ) : (
              <div style={{
                height: 200, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                color: "var(--text-muted)", gap: 12,
              }}>
                <BrainCircuit size={48} style={{ opacity: 0.2 }} />
                <div style={{ fontWeight: 500 }}>Configure and start training to see progress</div>
              </div>
            )}
          </div>

          {/* Saved models */}
          <div className="card" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                Saved Models
              </h2>
              <button onClick={fetchModels} className="btn btn-ghost" style={{ padding: "4px 8px", fontSize: "0.8125rem", display: "flex", alignItems: "center", gap: 6 }}>
                <RefreshCw size={13} /> Refresh
              </button>
            </div>
            {models.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", textAlign: "center", padding: "24px 0" }}>
                No models saved yet. Train an agent to save a model.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {models.map((m) => (
                  <div key={m.model_id} style={{
                    display: "flex", alignItems: "center", gap: 12,
                    padding: "14px 16px", borderRadius: "var(--radius-md)",
                    background: "var(--surface-elevated)", border: "1px solid var(--border)",
                  }}>
                    <div style={{
                      width: 36, height: 36, borderRadius: 8,
                      background: "linear-gradient(135deg, #8b5cf6, #ec4899)",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      flexShrink: 0,
                    }}>
                      <BrainCircuit size={18} color="#fff" />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 600, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {m.model_name || m.model_id}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {m.episodes_trained} episodes · Best reward: {m.best_reward?.toFixed(4) ?? "—"} · {new Date(m.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <div style={{
                        padding: "4px 10px", borderRadius: 6, fontSize: "0.75rem", fontWeight: 600,
                        color: "#22c55e", background: "rgba(34,197,94,0.1)",
                        display: "flex", alignItems: "center", gap: 4,
                      }}>
                        <ChevronRight size={12} /> Use for Schedule
                      </div>
                      <button
                        id={`btn-delete-model-${m.model_id}`}
                        onClick={() => handleDeleteModel(m.model_id)}
                        className="btn btn-ghost"
                        style={{ width: 30, height: 30, padding: 0, color: "var(--error)" }}
                        title="Delete model"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
