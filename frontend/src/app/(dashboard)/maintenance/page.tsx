"use client";

import React, { useEffect, useState, useCallback } from "react";
import { ShieldAlert, AlertTriangle, CheckCircle2, RefreshCw, Zap, TrendingUp, Activity, Server } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────

interface MachineHealth {
  id: number;
  machine_id: string;
  timestamp: string;
  temperature: number;
  vibration: number;
  load_pct: number;
  failure_probability: number;
  anomaly_score?: number;
}

interface MaintenanceAlert {
  id: number;
  machine_id: string;
  created_at: string;
  predicted_failure_at?: string;
  severity: "low" | "medium" | "high" | "critical";
  failure_probability: number;
  recommended_action?: string;
  resolved: boolean;
  resolved_at?: string;
}

interface ForecastItem {
  machine_id: string;
  failure_probability: number;
  severity: string;
  predicted_failure_at?: string;
  recommended_action?: string;
  unavailability_windows: [number, number][];
}

// ─── Severity helpers ─────────────────────────────────────────────────────────

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

const SEVERITY_BG: Record<string, string> = {
  critical: "rgba(239,68,68,0.12)",
  high: "rgba(249,115,22,0.12)",
  medium: "rgba(234,179,8,0.12)",
  low: "rgba(34,197,94,0.12)",
};

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 10px",
        borderRadius: 99,
        fontSize: "0.75rem",
        fontWeight: 700,
        letterSpacing: "0.04em",
        color: SEVERITY_COLORS[severity] || "var(--text-muted)",
        background: SEVERITY_BG[severity] || "transparent",
        border: `1px solid ${SEVERITY_COLORS[severity] || "var(--border)"}22`,
        textTransform: "uppercase",
      }}
    >
      {severity}
    </span>
  );
}

// ─── Failure probability ring ─────────────────────────────────────────────────

function ProbabilityRing({
  probability,
  size = 96,
}: {
  probability: number;
  size?: number;
}) {
  const r = (size - 16) / 2;
  const circumference = 2 * Math.PI * r;
  const dashOffset = circumference * (1 - probability);
  const color =
    probability >= 0.8 ? "#ef4444" :
    probability >= 0.6 ? "#f97316" :
    probability >= 0.35 ? "#eab308" : "#22c55e";

  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="var(--border)" strokeWidth={8}
      />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={8}
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 1s ease" }}
      />
      <text
        x="50%" y="50%"
        textAnchor="middle" dominantBaseline="central"
        fill={color} fontSize={size * 0.2} fontWeight={700}
        style={{ transform: `rotate(90deg)`, transformOrigin: "50% 50%" }}
      >
        {Math.round(probability * 100)}%
      </text>
    </svg>
  );
}

// ─── Sparkline chart ──────────────────────────────────────────────────────────

function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return <div style={{ height: 36 }} />;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const w = 120, h = 36;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1].split(",")[0]} cy={pts[pts.length - 1].split(",")[1]} r={3} fill={color} />
    </svg>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function MaintenancePage() {
  const [alerts, setAlerts] = useState<MaintenanceAlert[]>([]);
  const [healthMap, setHealthMap] = useState<Record<string, MachineHealth[]>>({});
  const [forecast, setForecast] = useState<Record<string, ForecastItem>>({});
  const [loading, setLoading] = useState(false);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const machineIds = ["M1", "M2", "M3", "M4", "M5"];

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch alerts
      const alertsRes = await fetch(`${API_BASE}/api/maintenance/alerts?resolved=false`);
      if (alertsRes.ok) setAlerts(await alertsRes.json());

      // Fetch health history for each machine
      const map: Record<string, MachineHealth[]> = {};
      await Promise.all(
        machineIds.map(async (mid) => {
          const res = await fetch(`${API_BASE}/api/maintenance/history/${mid}?limit=24`);
          if (res.ok) map[mid] = (await res.json()).reverse();
        })
      );
      setHealthMap(map);

      // Fetch forecast
      const fcRes = await fetch(`${API_BASE}/api/maintenance/forecast?machine_ids=${machineIds.join(",")}`);
      if (fcRes.ok) {
        const fc = await fcRes.json();
        setForecast(fc.windows || {});
      }
    } catch {
      setError("Failed to load maintenance data. Ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAutoIngest = async () => {
    setIngestLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/maintenance/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          auto_generate: true,
          machine_ids: machineIds,
          n_readings: 24,
        }),
      });
      if (res.ok) {
        await fetchData();
      }
    } finally {
      setIngestLoading(false);
    }
  };

  const handleResolveAlert = async (alertId: number) => {
    await fetch(`${API_BASE}/api/maintenance/alerts/${alertId}/resolve`, { method: "POST" });
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
  };

  useEffect(() => { fetchData(); }, [fetchData]);

  const latestHealth = Object.fromEntries(
    Object.entries(healthMap).map(([mid, readings]) => [mid, readings[readings.length - 1]])
  );

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const highCount = alerts.filter((a) => a.severity === "high").length;

  return (
    <div style={{ padding: "32px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10,
              background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <ShieldAlert size={20} color="#fff" />
            </div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Predictive Maintenance
            </h1>
          </div>
          <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.9375rem" }}>
            AI-powered anomaly detection and failure forecasting for shop floor machines
          </p>
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <button
            id="btn-ingest-sensors"
            onClick={handleAutoIngest}
            disabled={ingestLoading}
            className="btn btn-primary"
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <Zap size={16} />
            {ingestLoading ? "Ingesting…" : "Simulate Sensors"}
          </button>
          <button
            id="btn-refresh-maintenance"
            onClick={fetchData}
            disabled={loading}
            className="btn btn-ghost"
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <RefreshCw size={16} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          padding: "12px 16px", borderRadius: "var(--radius-md)",
          background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)",
          color: "var(--error)", marginBottom: 24, display: "flex", alignItems: "center", gap: 10,
        }}>
          <AlertTriangle size={16} /> {error}
        </div>
      )}

      {/* KPI summary row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        {[
          { label: "Active Alerts", value: alerts.length, icon: ShieldAlert, color: "#ef4444" },
          { label: "Critical", value: criticalCount, icon: AlertTriangle, color: "#ef4444" },
          { label: "High Risk", value: highCount, icon: TrendingUp, color: "#f97316" },
          { label: "Machines Monitored", value: machineIds.length, icon: Server, color: "#8b5cf6" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="card" style={{ padding: "20px 24px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{
                width: 40, height: 40, borderRadius: 10,
                background: `${color}18`,
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Icon size={20} color={color} />
              </div>
              <div>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text-primary)" }}>{value}</div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{label}</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
        {/* Machine health cards */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 20, color: "var(--text-primary)" }}>
            Machine Health Status
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {machineIds.map((mid) => {
              const h = latestHealth[mid];
              const fc = forecast[mid];
              const prob = h?.failure_probability ?? fc?.failure_probability ?? 0;
              const history = healthMap[mid] ?? [];
              return (
                <div key={mid} style={{
                  display: "flex", alignItems: "center", gap: 16,
                  padding: "16px", borderRadius: "var(--radius-md)",
                  background: "var(--surface-elevated)",
                  border: "1px solid var(--border)",
                }}>
                  <ProbabilityRing probability={prob} size={72} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{mid}</span>
                      <SeverityBadge severity={fc?.severity ?? (prob < 0.35 ? "low" : prob < 0.6 ? "medium" : "high")} />
                    </div>
                    {h ? (
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
                        {[
                          { label: "Temp", value: `${h.temperature.toFixed(1)}°C`, data: history.map(r => r.temperature), color: "#f97316" },
                          { label: "Vib", value: `${h.vibration.toFixed(2)} mm/s`, data: history.map(r => r.vibration), color: "#8b5cf6" },
                          { label: "Load", value: `${h.load_pct.toFixed(0)}%`, data: history.map(r => r.load_pct), color: "#0ea5e9" },
                        ].map(({ label, value, data, color: c }) => (
                          <div key={label} style={{ textAlign: "center" }}>
                            <Sparkline values={data} color={c} />
                            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>{value}</div>
                            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>{label}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No data yet — click "Simulate Sensors"</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Active Alerts */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 20, color: "var(--text-primary)" }}>
            Active Alerts
          </h2>
          {alerts.length === 0 ? (
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", gap: 12, padding: "48px 0",
              color: "var(--text-muted)",
            }}>
              <CheckCircle2 size={40} style={{ opacity: 0.4 }} />
              <div style={{ fontWeight: 500 }}>All clear — no active alerts</div>
              <div style={{ fontSize: "0.8125rem" }}>Click "Simulate Sensors" to generate readings</div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12, maxHeight: 520, overflowY: "auto" }}>
              {alerts.map((alert) => (
                <div key={alert.id} style={{
                  padding: "14px 16px", borderRadius: "var(--radius-md)",
                  background: SEVERITY_BG[alert.severity] || "var(--surface-elevated)",
                  border: `1px solid ${SEVERITY_COLORS[alert.severity] || "var(--border)"}30`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{alert.machine_id}</span>
                      <SeverityBadge severity={alert.severity} />
                    </div>
                    <button
                      id={`btn-resolve-alert-${alert.id}`}
                      onClick={() => handleResolveAlert(alert.id)}
                      className="btn btn-ghost"
                      style={{ padding: "2px 10px", fontSize: "0.75rem", height: 24, color: "#22c55e" }}
                    >
                      Resolve
                    </button>
                  </div>
                  <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 4 }}>
                    Failure probability: <strong>{Math.round(alert.failure_probability * 100)}%</strong>
                    {alert.predicted_failure_at && (
                      <> · Predicted: <strong>{new Date(alert.predicted_failure_at).toLocaleString()}</strong></>
                    )}
                  </div>
                  {alert.recommended_action && (
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                      {alert.recommended_action}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Forecast / Unavailability Windows */}
      {Object.keys(forecast).length > 0 && (
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
            <Activity size={18} />
            Maintenance Forecast — Predicted Unavailability Windows
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginBottom: 20 }}>
            These windows can be copied into a new schedule upload to proactively avoid scheduling operations on at-risk machines.
          </p>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr>
                  {["Machine", "Failure Prob.", "Severity", "Predicted Failure At", "Unavailability Window", "Action"].map((h) => (
                    <th key={h} style={{ textAlign: "left", padding: "8px 12px", color: "var(--text-muted)", fontWeight: 600, borderBottom: "1px solid var(--border)", fontSize: "0.75rem", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.values(forecast).map((fc) => (
                  <tr key={fc.machine_id} style={{ borderBottom: "1px solid var(--border)" }}>
                    <td style={{ padding: "12px 12px", fontWeight: 600, color: "var(--text-primary)" }}>{fc.machine_id}</td>
                    <td style={{ padding: "12px 12px" }}>{Math.round(fc.failure_probability * 100)}%</td>
                    <td style={{ padding: "12px 12px" }}><SeverityBadge severity={fc.severity} /></td>
                    <td style={{ padding: "12px 12px", color: "var(--text-secondary)" }}>
                      {fc.predicted_failure_at ? new Date(fc.predicted_failure_at).toLocaleString() : "N/A"}
                    </td>
                    <td style={{ padding: "12px 12px", fontFamily: "monospace", fontSize: "0.8125rem" }}>
                      {fc.unavailability_windows.length > 0
                        ? fc.unavailability_windows.map(([s, e]) => `(${s.toFixed(0)}–${e.toFixed(0)})`).join(", ")
                        : "—"}
                    </td>
                    <td style={{ padding: "12px 12px", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                      {fc.recommended_action ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
