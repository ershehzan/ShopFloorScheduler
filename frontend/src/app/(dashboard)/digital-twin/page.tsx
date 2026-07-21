"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { Cpu, Play, Square, Zap, AlertTriangle, CheckCircle2, RefreshCw, Package } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const WS_BASE = API_BASE.replace("http", "ws");

// ─── Types ────────────────────────────────────────────────────────────────────

interface HistoryRun {
  task_id: string;
  created_at: string;
  status: string;
  algorithm: string;
  makespan?: number;
  file_name?: string;
}

interface TwinSession {
  session_id: string;
  task_id: string;
  status: string;
  speed_factor: number;
  created_at: string;
  ws_url: string;
}

interface SimEvent {
  event_type: string;
  virtual_time: number;
  payload: Record<string, unknown>;
  real_timestamp: string;
}

interface GanttOp {
  job_id: number;
  op_index: number;
  machine_id: number | string;
  start_time: number;
  end_time: number;
}

// ─── Color helpers ────────────────────────────────────────────────────────────

const JOB_COLORS = ["#8b5cf6", "#0ea5e9", "#22c55e", "#f97316", "#ec4899", "#eab308", "#14b8a6", "#f43f5e"];

function jobColor(jobId: number | string): string {
  return JOB_COLORS[Number(jobId) % JOB_COLORS.length];
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  op_start: <Play size={12} />,
  op_end: <CheckCircle2 size={12} />,
  machine_alert: <AlertTriangle size={12} />,
  breakdown: <Square size={12} />,
  rush_order: <Package size={12} />,
  sim_complete: <CheckCircle2 size={12} />,
};

const EVENT_COLORS: Record<string, string> = {
  op_start: "#8b5cf6",
  op_end: "#22c55e",
  machine_alert: "#f97316",
  breakdown: "#ef4444",
  rush_order: "#0ea5e9",
  sim_complete: "#22c55e",
  error: "#ef4444",
};

// ─── Animated Gantt ───────────────────────────────────────────────────────────

interface AnimatedGanttProps {
  schedule: GanttOp[];
  activeOps: Set<string>;    // "job_id:op_index"
  completedOps: Set<string>;
  breakdown: Record<string, boolean>;
  virtualTime: number;
}

function AnimatedGantt({ schedule, activeOps, completedOps, breakdown, virtualTime }: AnimatedGanttProps) {
  const machineIds = [...new Set(schedule.map((op) => op.machine_id))].sort((a, b) => Number(a) - Number(b));
  const maxTime = Math.max(...schedule.map((op) => op.end_time), 1);
  const ROW_H = 44;
  const LABEL_W = 80;
  const BAR_H = 28;
  const totalWidth = 800;
  const chartWidth = totalWidth - LABEL_W;

  const timeToX = (t: number) => (t / maxTime) * chartWidth;

  return (
    <div style={{ overflowX: "auto" }}>
      <svg width={totalWidth} height={machineIds.length * ROW_H + 24}>
        {/* Timeline ticks */}
        {Array.from({ length: 11 }, (_, i) => {
          const t = (i / 10) * maxTime;
          const x = LABEL_W + timeToX(t);
          return (
            <g key={i}>
              <line x1={x} y1={0} x2={x} y2={machineIds.length * ROW_H} stroke="var(--border)" strokeWidth={1} strokeDasharray="2,4" />
              <text x={x} y={machineIds.length * ROW_H + 16} textAnchor="middle" fontSize={9} fill="var(--text-muted)">{Math.round(t)}</text>
            </g>
          );
        })}

        {/* Virtual time cursor */}
        {(() => {
          const cx = LABEL_W + timeToX(virtualTime);
          return (
            <g>
              <line x1={cx} y1={0} x2={cx} y2={machineIds.length * ROW_H} stroke="#8b5cf6" strokeWidth={2} opacity={0.8} />
              <circle cx={cx} cy={0} r={4} fill="#8b5cf6" />
            </g>
          );
        })()}

        {machineIds.map((mid, rowIdx) => {
          const y = rowIdx * ROW_H;
          const isDown = breakdown[String(mid)];
          return (
            <g key={String(mid)}>
              {/* Row background */}
              <rect
                x={LABEL_W} y={y} width={chartWidth} height={ROW_H}
                fill={isDown ? "rgba(239,68,68,0.06)" : "transparent"}
              />
              {/* Machine label */}
              <text x={LABEL_W - 8} y={y + ROW_H / 2 + 4} textAnchor="end" fontSize={12} fontWeight={600} fill={isDown ? "#ef4444" : "var(--text-secondary)"}>
                M{mid}
              </text>
              {/* Operations for this machine */}
              {schedule.filter((op) => String(op.machine_id) === String(mid)).map((op) => {
                const key = `${op.job_id}:${op.op_index}`;
                const isActive = activeOps.has(key);
                const isDone = completedOps.has(key);
                const x = LABEL_W + timeToX(op.start_time);
                const barW = Math.max(timeToX(op.end_time - op.start_time), 4);
                const color = jobColor(op.job_id);
                const opacity = isDone ? 0.9 : isActive ? 1.0 : 0.25;

                return (
                  <g key={key}>
                    <rect
                      x={x} y={y + (ROW_H - BAR_H) / 2}
                      width={barW} height={BAR_H}
                      rx={4}
                      fill={color}
                      opacity={opacity}
                      style={{ transition: "opacity 0.3s ease" }}
                    />
                    {isActive && (
                      <rect
                        x={x} y={y + (ROW_H - BAR_H) / 2}
                        width={barW} height={BAR_H}
                        rx={4}
                        fill="white"
                        opacity={0.12}
                        style={{ animation: "pulse 1.5s ease-in-out infinite" }}
                      />
                    )}
                    {barW > 20 && (
                      <text
                        x={x + barW / 2} y={y + ROW_H / 2 + 4}
                        textAnchor="middle" fontSize={10} fontWeight={700} fill="white"
                      >
                        J{op.job_id}
                      </text>
                    )}
                  </g>
                );
              })}

              {/* Separator */}
              <line x1={0} y1={y + ROW_H} x2={totalWidth} y2={y + ROW_H} stroke="var(--border)" strokeWidth={0.5} />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function DigitalTwinPage() {
  const [runs, setRuns] = useState<HistoryRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [speedFactor, setSpeedFactor] = useState(20);
  const [injectFailures, setInjectFailures] = useState(true);
  const [session, setSession] = useState<TwinSession | null>(null);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [virtualTime, setVirtualTime] = useState(0);
  const [schedule, setSchedule] = useState<GanttOp[]>([]);
  const [activeOps, setActiveOps] = useState<Set<string>>(new Set());
  const [completedOps, setCompletedOps] = useState<Set<string>>(new Set());
  const [breakdownMachines, setBreakdownMachines] = useState<Record<string, boolean>>({});
  const [injectMachine, setInjectMachine] = useState("");
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Fetch completed runs for dropdown
  useEffect(() => {
    const fetchRuns = async () => {
      const res = await fetch(`${API_BASE}/api/history?page=1&page_size=20&status=complete`);
      if (res.ok) {
        const data = await res.json();
        setRuns(data.items || []);
      }
    };
    fetchRuns();
  }, []);

  // Fetch schedule data for selected run
  useEffect(() => {
    if (!selectedRun) return;
    const fetchSchedule = async () => {
      const res = await fetch(`${API_BASE}/api/schedule/results/${selectedRun}`);
      if (res.ok) {
        const data = await res.json();
        if (data.result?.schedule) {
          setSchedule(data.result.schedule);
        }
      }
    };
    fetchSchedule();
  }, [selectedRun]);

  const connectWS = useCallback((wsUrl: string) => {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(`${WS_BASE}${wsUrl}`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const evt: SimEvent = JSON.parse(e.data);
        setVirtualTime(evt.virtual_time);
        setEvents((prev) => [...prev.slice(-199), evt]);

        if (evt.event_type === "op_start") {
          const key = `${evt.payload.job_id}:${evt.payload.op_index}`;
          setActiveOps((prev) => new Set([...prev, key]));
        } else if (evt.event_type === "op_end") {
          const key = `${evt.payload.job_id}:${evt.payload.op_index}`;
          setActiveOps((prev) => { const s = new Set(prev); s.delete(key); return s; });
          setCompletedOps((prev) => new Set([...prev, key]));
        } else if (evt.event_type === "breakdown") {
          setBreakdownMachines((prev) => ({ ...prev, [String(evt.payload.machine_id)]: true }));
        }

        eventsEndRef.current?.scrollIntoView({ behavior: "smooth" });
      } catch {}
    };
    ws.onclose = () => {};
  }, []);

  const handleStart = async () => {
    if (!selectedRun) return;
    setLoading(true);
    setEvents([]);
    setActiveOps(new Set());
    setCompletedOps(new Set());
    setBreakdownMachines({});
    setVirtualTime(0);
    try {
      const res = await fetch(`${API_BASE}/api/twin/start/${selectedRun}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id: selectedRun, speed_factor: speedFactor, inject_failures: injectFailures }),
      });
      if (res.ok) {
        const s: TwinSession = await res.json();
        setSession(s);
        connectWS(s.ws_url);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStop = () => {
    if (wsRef.current) wsRef.current.close();
    if (session) {
      fetch(`${API_BASE}/api/twin/sessions/${session.session_id}`, { method: "DELETE" });
      setSession(null);
    }
  };

  const handleInjectBreakdown = async () => {
    if (!session || !injectMachine) return;
    await fetch(`${API_BASE}/api/twin/sessions/${session.session_id}/inject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ disruption_type: "breakdown", machine_id: injectMachine }),
    });
  };

  useEffect(() => () => { wsRef.current?.close(); }, []);

  const selectedRunData = runs.find((r) => r.task_id === selectedRun);
  const maxTime = schedule.length > 0 ? Math.max(...schedule.map((op) => op.end_time)) : 0;

  return (
    <div style={{ padding: "32px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 10,
              background: "linear-gradient(135deg, #0ea5e9, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Cpu size={20} color="#fff" />
            </div>
            <h1 style={{ fontSize: "1.75rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
              Digital Twin
            </h1>
          </div>
          <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.9375rem" }}>
            Real-time virtual replica of your shop floor — replay schedules and simulate disruptions
          </p>
        </div>
        {session && (
          <div style={{
            padding: "6px 14px", borderRadius: 99,
            background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.3)",
            color: "#22c55e", fontSize: "0.8125rem", fontWeight: 600,
            display: "flex", alignItems: "center", gap: 6,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: "50%", background: "#22c55e",
              animation: "pulse 1.5s ease-in-out infinite",
            }} />
            Session Active
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 24 }}>
        {/* Control panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div className="card" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 20, color: "var(--text-primary)" }}>
              Simulation Control
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Select Schedule Run
                </label>
                <select
                  id="twin-run-select"
                  value={selectedRun}
                  onChange={(e) => setSelectedRun(e.target.value)}
                  className="form-input"
                  style={{ width: "100%" }}
                >
                  <option value="">— Choose a completed run —</option>
                  {runs.map((r) => (
                    <option key={r.task_id} value={r.task_id}>
                      {r.algorithm} · {r.makespan ? `Makespan: ${r.makespan}` : ""} · {new Date(r.created_at).toLocaleDateString()}
                    </option>
                  ))}
                </select>
                {runs.length === 0 && (
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                    No completed runs found. Run a schedule first.
                  </div>
                )}
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Speed Factor: <span style={{ color: "var(--accent)" }}>{speedFactor}×</span>
                </label>
                <input
                  id="twin-speed"
                  type="range" min={1} max={200} step={1}
                  value={speedFactor}
                  onChange={(e) => setSpeedFactor(Number(e.target.value))}
                  style={{ width: "100%" }}
                />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  <span>1× (slow)</span><span>200× (fast)</span>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <input
                  id="twin-inject-failures"
                  type="checkbox"
                  checked={injectFailures}
                  onChange={(e) => setInjectFailures(e.target.checked)}
                  style={{ width: 16, height: 16, accentColor: "var(--accent)" }}
                />
                <label htmlFor="twin-inject-failures" style={{ fontSize: "0.875rem", color: "var(--text-secondary)", cursor: "pointer" }}>
                  Auto-inject random failures
                </label>
              </div>

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  id="btn-twin-start"
                  onClick={handleStart}
                  disabled={!selectedRun || loading || !!session}
                  className="btn btn-primary"
                  style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}
                >
                  <Play size={15} />
                  {loading ? "Starting…" : "Start Twin"}
                </button>
                <button
                  id="btn-twin-stop"
                  onClick={handleStop}
                  disabled={!session}
                  className="btn btn-ghost"
                  style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, color: session ? "var(--error)" : undefined }}
                >
                  <Square size={15} />
                  Stop
                </button>
              </div>
            </div>
          </div>

          {/* Disruption injection */}
          <div className="card" style={{ padding: "24px" }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16, color: "var(--text-primary)" }}>
              Inject Disruption
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 600, marginBottom: 6, color: "var(--text-secondary)" }}>
                  Machine ID (for breakdown)
                </label>
                <input
                  id="twin-inject-machine"
                  type="text"
                  value={injectMachine}
                  onChange={(e) => setInjectMachine(e.target.value)}
                  placeholder="e.g. 1"
                  className="form-input"
                  style={{ width: "100%" }}
                />
              </div>
              <button
                id="btn-inject-breakdown"
                onClick={handleInjectBreakdown}
                disabled={!session || !injectMachine}
                className="btn btn-ghost"
                style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, color: "#ef4444", borderColor: "rgba(239,68,68,0.3)" }}
              >
                <AlertTriangle size={15} />
                Inject Breakdown
              </button>
            </div>
          </div>

          {/* Stats */}
          {schedule.length > 0 && (
            <div className="card" style={{ padding: "20px 24px" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Schedule Info
              </div>
              {[
                { label: "Algorithm", value: selectedRunData?.algorithm ?? "—" },
                { label: "Total Ops", value: schedule.length },
                { label: "Makespan", value: maxTime },
                { label: "Virtual Time", value: virtualTime.toFixed(1) },
                { label: "Progress", value: `${Math.min(100, Math.round((virtualTime / maxTime) * 100))}%` },
              ].map(({ label, value }) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)", fontSize: "0.875rem" }}>
                  <span style={{ color: "var(--text-muted)" }}>{label}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Main visualization */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Animated Gantt */}
          <div className="card" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                Live Gantt Replay
              </h2>
              {session && (
                <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                  Virtual time: <strong style={{ color: "var(--text-primary)" }}>{virtualTime.toFixed(1)}</strong>
                </div>
              )}
            </div>

            {schedule.length > 0 ? (
              <>
                {/* Time progress */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ height: 4, borderRadius: 99, background: "var(--border)", overflow: "hidden" }}>
                    <div style={{
                      height: "100%", borderRadius: 99,
                      background: "linear-gradient(90deg, #0ea5e9, #8b5cf6)",
                      width: `${Math.min(100, (virtualTime / maxTime) * 100)}%`,
                      transition: "width 0.3s ease",
                    }} />
                  </div>
                </div>
                <AnimatedGantt
                  schedule={schedule}
                  activeOps={activeOps}
                  completedOps={completedOps}
                  breakdown={breakdownMachines}
                  virtualTime={virtualTime}
                />
                {/* Legend */}
                <div style={{ display: "flex", gap: 20, marginTop: 16, flexWrap: "wrap" }}>
                  {[...new Set(schedule.map((op) => op.job_id))].sort((a, b) => Number(a) - Number(b)).map((jid) => (
                    <div key={jid} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <div style={{ width: 12, height: 12, borderRadius: 3, background: jobColor(jid) }} />
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Job {jid}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{
                height: 200, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                color: "var(--text-muted)", gap: 12,
              }}>
                <Cpu size={48} style={{ opacity: 0.2 }} />
                <div style={{ fontWeight: 500 }}>Select a completed run and click "Start Twin"</div>
              </div>
            )}
          </div>

          {/* Event log */}
          <div className="card" style={{ padding: "24px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <h2 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>
                Event Log
              </h2>
              <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                {events.length} events
              </span>
            </div>
            <div style={{
              maxHeight: 280, overflowY: "auto",
              display: "flex", flexDirection: "column", gap: 4,
              fontFamily: "monospace",
            }}>
              {events.length === 0 ? (
                <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", textAlign: "center", padding: "24px 0" }}>
                  Events will appear here when the simulation runs…
                </div>
              ) : (
                events.map((evt, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: 8,
                    padding: "4px 8px", borderRadius: 6,
                    background: i === events.length - 1 ? "rgba(139,92,246,0.08)" : "transparent",
                    fontSize: "0.8125rem",
                  }}>
                    <span style={{ color: EVENT_COLORS[evt.event_type] ?? "var(--text-muted)", flexShrink: 0 }}>
                      {EVENT_ICONS[evt.event_type] ?? <Zap size={12} />}
                    </span>
                    <span style={{ color: "var(--text-muted)", flexShrink: 0, fontSize: "0.75rem" }}>
                      t={evt.virtual_time.toFixed(1)}
                    </span>
                    <span style={{ color: EVENT_COLORS[evt.event_type] ?? "var(--text-secondary)", fontWeight: 500, flexShrink: 0 }}>
                      {evt.event_type}
                    </span>
                    <span style={{ color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {JSON.stringify(evt.payload)}
                    </span>
                  </div>
                ))
              )}
              <div ref={eventsEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
