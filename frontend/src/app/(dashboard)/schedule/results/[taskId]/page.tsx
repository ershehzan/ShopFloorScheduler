"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw, Loader2, AlertTriangle, Zap, Play, Plus, Trash2, Clock } from "lucide-react";
import KPICards from "@/components/results/KPICards";
import ExportButtons from "@/components/results/ExportButtons";
import GanttChart from "@/components/gantt/GanttChart";
import { getResults, StatusResponse, rescheduleBreakdown, rescheduleRushOrder } from "@/lib/api";

export default function ResultsPage({ params }: { params: Promise<{ taskId: string }> }) {
  const router = useRouter();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [data, setData] = useState<StatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    params.then((p) => setTaskId(p.taskId));
  }, [params]);

  useEffect(() => {
    if (!taskId) return;
    getResults(taskId)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load results.");
        setLoading(false);
      });
  }, [taskId]);

  // Rescheduling states
  const [activeTab, setActiveTab] = useState<"breakdown" | "rush">("breakdown");
  const [rescheduleLoading, setRescheduleLoading] = useState(false);
  const [rescheduleError, setRescheduleError] = useState<string | null>(null);

  // Breakdown fields
  const [brokenMachine, setBrokenMachine] = useState("");
  const [downtimeStart, setDowntimeStart] = useState("");
  const [downtimeEnd, setDowntimeEnd] = useState("");

  // Rush order fields
  const [rushJobId, setRushJobId] = useState("");
  const [rushDueDate, setRushDueDate] = useState("");
  const [rushPriority, setRushPriority] = useState("10");
  const [rushOps, setRushOps] = useState<{ machine_id: number; processing_time: number }[]>([
    { machine_id: 1, processing_time: 5 },
  ]);

  const handleAddRushOp = () => {
    // Select first machine or default to 0
    const defMachine = result?.utilization?.[0]?.machine_id ?? 0;
    setRushOps((prev) => [...prev, { machine_id: defMachine, processing_time: 5 }]);
  };

  const handleRemoveRushOp = (index: number) => {
    setRushOps((prev) => prev.filter((_, i) => i !== index));
  };

  const handleRushOpChange = (index: number, field: "machine_id" | "processing_time", value: number) => {
    setRushOps((prev) =>
      prev.map((op, i) => (i === index ? { ...op, [field]: value } : op))
    );
  };

  const handleBreakdownSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskId || !brokenMachine || !downtimeStart || !downtimeEnd) return;

    setRescheduleLoading(true);
    setRescheduleError(null);

    try {
      const res = await rescheduleBreakdown({
        task_id: taskId,
        machine_id: parseInt(brokenMachine),
        downtime_start: parseInt(downtimeStart),
        downtime_end: parseInt(downtimeEnd),
      });
      router.push(`/schedule/status/${res.task_id}`);
    } catch (err) {
      setRescheduleError(err instanceof Error ? err.message : "Rescheduling failed.");
      setRescheduleLoading(false);
    }
  };

  const handleRushSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskId || !rushJobId || !rushDueDate || rushOps.length === 0) return;

    setRescheduleLoading(true);
    setRescheduleError(null);

    try {
      const res = await rescheduleRushOrder({
        task_id: taskId,
        rush_job: {
          job_id: parseInt(rushJobId),
          due_date: parseInt(rushDueDate),
          priority: parseInt(rushPriority),
          operations: rushOps,
        },
      });
      router.push(`/schedule/status/${res.task_id}`);
    } catch (err) {
      setRescheduleError(err instanceof Error ? err.message : "Rush order injection failed.");
      setRescheduleLoading(false);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 400,
          gap: 16,
          color: "var(--text-muted)",
        }}
      >
        <Loader2 size={32} className="animate-spin" style={{ color: "var(--secondary)" }} />
        <p style={{ fontSize: "0.9375rem" }}>Loading results...</p>
      </div>
    );
  }

  if (error || !data?.result) {
    return (
      <div style={{ maxWidth: 640, margin: "0 auto" }}>
        <div
          className="card"
          style={{
            background: "rgba(239,68,68,0.04)",
            borderColor: "rgba(239,68,68,0.2)",
            textAlign: "center",
            padding: 40,
          }}
        >
          <p style={{ color: "var(--error)", fontWeight: 600, marginBottom: 8 }}>Results unavailable</p>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: 20 }}>
            {error ?? "No results found for this task ID."}
          </p>
          <button
            onClick={() => router.push("/schedule/new")}
            className="btn btn-primary"
          >
            Start New Schedule
          </button>
        </div>
      </div>
    );
  }

  const result = data.result;

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 32,
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <button
            onClick={() => router.push("/dashboard")}
            className="btn btn-ghost"
            style={{ height: 32, fontSize: "0.875rem", gap: 6, marginBottom: 12, padding: "0 8px" }}
          >
            <ArrowLeft size={14} />
            Dashboard
          </button>
          <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Schedule Results</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
            Optimization complete · Task{" "}
            <code
              style={{
                fontSize: "0.8125rem",
                background: "var(--bg-secondary)",
                padding: "2px 6px",
                borderRadius: 4,
                fontFamily: "monospace",
              }}
            >
              {taskId}
            </code>
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <ExportButtons
            taskId={taskId ?? ""}
            excelUrl={result.excel_url}
            chartUrl={result.chart_url}
          />
          <button
            onClick={() => router.push("/schedule/new")}
            className="btn btn-secondary"
            id="rerun-btn"
            style={{ gap: 8, height: 40, fontSize: "0.875rem" }}
          >
            <RefreshCw size={14} />
            Re-run
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Performance Metrics</h2>
        <KPICards
          makespan={result.makespan}
          totalTardiness={result.total_tardiness}
          avgFlowTime={result.avg_flow_time}
          onTimePercent={result.on_time_percent}
          algorithm={result.algorithm}
        />
      </div>

      {/* Gantt Chart */}
      {result.schedule.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 4 }}>
            Interactive Gantt Chart
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: 20 }}>
            Hover over operations for details. Use zoom controls to adjust the time axis.
          </p>
          <GanttChart schedule={result.schedule} makespan={result.makespan} />
        </div>
      )}

      {/* Machine Utilization */}
      {result.utilization.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Machine Utilization</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {result.utilization
              .slice()
              .sort((a, b) => b.utilization - a.utilization)
              .map(({ machine_id, utilization }) => (
                <div key={machine_id}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 4,
                      fontSize: "0.875rem",
                    }}
                  >
                    <span style={{ color: "var(--text-secondary)", fontWeight: 500 }}>
                      Machine {machine_id}
                    </span>
                    <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                      {(utilization * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div
                    style={{
                      height: 8,
                      background: "var(--bg-secondary)",
                      borderRadius: 99,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${utilization * 100}%`,
                        height: "100%",
                        background:
                          utilization > 0.8
                            ? "var(--success)"
                            : utilization > 0.5
                            ? "var(--secondary)"
                            : "var(--warning)",
                        borderRadius: 99,
                        transition: "width 1s ease",
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Dynamic Rescheduling Section */}
      {result.schedule.length > 0 && (
        <div className="card" style={{ marginBottom: 24, padding: 24 }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: 4, display: "flex", alignItems: "center", gap: 8 }}>
            <RefreshCw size={18} className="animate-spin-slow" />
            Dynamic Rescheduling Control Room
          </h2>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: 20 }}>
            Respond to live factory disturbances by reporting breakdowns or injecting urgent rush orders.
          </p>

          {/* Tabs */}
          <div style={{ display: "flex", gap: 8, marginBottom: 20, borderBottom: "1px solid var(--border)", paddingBottom: 10 }}>
            <button
              onClick={() => setActiveTab("breakdown")}
              type="button"
              className={`btn ${activeTab === "breakdown" ? "btn-primary" : "btn-ghost"}`}
              style={{ gap: 6, height: 36, fontSize: "0.875rem" }}
            >
              <AlertTriangle size={14} />
              Report Machine Breakdown
            </button>
            <button
              onClick={() => setActiveTab("rush")}
              type="button"
              className={`btn ${activeTab === "rush" ? "btn-primary" : "btn-ghost"}`}
              style={{ gap: 6, height: 36, fontSize: "0.875rem" }}
            >
              <Zap size={14} />
              Inject Rush Order
            </button>
          </div>

          {rescheduleError && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "12px 14px",
                background: "rgba(239,68,68,0.06)",
                border: "1px solid rgba(239,68,68,0.2)",
                borderRadius: "var(--radius-md)",
                color: "var(--error)",
                fontSize: "0.875rem",
                marginBottom: 16,
              }}
            >
              <AlertTriangle size={14} />
              {rescheduleError}
            </div>
          )}

          {/* Breakdown Form */}
          {activeTab === "breakdown" && (
            <form onSubmit={handleBreakdownSubmit}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, alignItems: "flex-end" }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    Select Broken Machine
                  </label>
                  <select
                    value={brokenMachine}
                    onChange={(e) => setBrokenMachine(e.target.value)}
                    className="input"
                    required
                    style={{ height: 38, background: "var(--bg-secondary)" }}
                  >
                    <option value="">-- Choose Machine --</option>
                    {result.utilization.map((u) => (
                      <option key={u.machine_id} value={u.machine_id}>
                        Machine {u.machine_id}
                      </option>
                    ))}
                  </select>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    Breakdown Start (Time Unit)
                  </label>
                  <input
                    type="number"
                    required
                    min="0"
                    value={downtimeStart}
                    onChange={(e) => setDowntimeStart(e.target.value)}
                    placeholder="e.g. 5"
                    className="input"
                    style={{ height: 38 }}
                  />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    Recovery End (Time Unit)
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={downtimeEnd}
                    onChange={(e) => setDowntimeEnd(e.target.value)}
                    placeholder="e.g. 15"
                    className="input"
                    style={{ height: 38 }}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ marginTop: 20, gap: 8, height: 38, width: "100%", justifyContent: "center" }}
                disabled={rescheduleLoading}
              >
                {rescheduleLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Generating Reschedule...
                  </>
                ) : (
                  <>
                    <Play size={14} />
                    Trigger Breakdown Rescheduling
                  </>
                )}
              </button>
            </form>
          )}

          {/* Rush Order Form */}
          {activeTab === "rush" && (
            <form onSubmit={handleRushSubmit}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 20 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    New Job ID
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={rushJobId}
                    onChange={(e) => setRushJobId(e.target.value)}
                    placeholder="e.g. 99"
                    className="input"
                    style={{ height: 38 }}
                  />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    Due Date (Time Unit)
                  </label>
                  <input
                    type="number"
                    required
                    min="0"
                    value={rushDueDate}
                    onChange={(e) => setRushDueDate(e.target.value)}
                    placeholder="e.g. 20"
                    className="input"
                    style={{ height: 38 }}
                  />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    Priority (1-20, default 10)
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    max="20"
                    value={rushPriority}
                    onChange={(e) => setRushPriority(e.target.value)}
                    className="input"
                    style={{ height: 38 }}
                  />
                </div>
              </div>

              {/* Operations Sequence */}
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 8, color: "var(--text-primary)" }}>
                  Operations Sequence (Order Matters)
                </h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 8, background: "var(--bg-secondary)", padding: 12, borderRadius: "var(--radius-md)" }}>
                  {rushOps.map((op, idx) => (
                    <div key={idx} style={{ display: "flex", gap: 12, alignItems: "center" }}>
                      <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)", width: 48 }}>
                        Op {idx + 1}
                      </span>
                      <select
                        value={op.machine_id}
                        onChange={(e) => handleRushOpChange(idx, "machine_id", parseInt(e.target.value))}
                        className="input"
                        style={{ flex: 1, height: 34, background: "var(--bg-primary)" }}
                      >
                        {result.utilization.map((u) => (
                          <option key={u.machine_id} value={u.machine_id}>
                            Machine {u.machine_id}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        required
                        min="1"
                        value={op.processing_time}
                        onChange={(e) => handleRushOpChange(idx, "processing_time", parseInt(e.target.value))}
                        placeholder="Duration"
                        className="input"
                        style={{ width: 100, height: 34 }}
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveRushOp(idx)}
                        disabled={rushOps.length === 1}
                        className="btn btn-ghost"
                        style={{ padding: 4, height: 34, width: 34, color: "var(--error)" }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={handleAddRushOp}
                    className="btn btn-ghost"
                    style={{ gap: 6, height: 32, fontSize: "0.8125rem", border: "1px dashed var(--border)", width: "100%", justifyContent: "center" }}
                  >
                    <Plus size={14} />
                    Add Operation Step
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ gap: 8, height: 38, width: "100%", justifyContent: "center" }}
                disabled={rescheduleLoading}
              >
                {rescheduleLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Injecting Rush Order...
                  </>
                ) : (
                  <>
                    <Zap size={14} />
                    Inject Rush Job into Schedule
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      )}

      {/* Operation Table */}
      {result.schedule.length > 0 && (
        <div className="card">
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Schedule Operations</h2>
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.875rem",
              }}
            >
              <thead>
                <tr>
                  {["Job", "Op #", "Machine", "Start", "End", "Duration"].map((col) => (
                    <th
                      key={col}
                      style={{
                        padding: "8px 16px",
                        textAlign: "left",
                        fontWeight: 600,
                        color: "var(--text-secondary)",
                        fontSize: "0.8125rem",
                        borderBottom: "1px solid var(--border)",
                        background: "var(--bg-secondary)",
                      }}
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.schedule
                  .slice()
                  .sort((a, b) => a.start_time - b.start_time)
                  .map((op, idx) => (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        transition: "background var(--transition-fast)",
                      }}
                    >
                      <td style={{ padding: "10px 16px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            fontWeight: 600,
                          }}
                        >
                          <span
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: 2,
                              background: `hsl(${(op.job_id * 47) % 360}, 70%, 50%)`,
                              flexShrink: 0,
                            }}
                          />
                          Job {op.job_id}
                        </span>
                      </td>
                      <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{op.op_index}</td>
                      <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>M{op.machine_id}</td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace" }}>{op.start_time}</td>
                      <td style={{ padding: "10px 16px", fontFamily: "monospace" }}>{op.end_time}</td>
                      <td
                        style={{
                          padding: "10px 16px",
                          fontWeight: 600,
                          color: "var(--secondary)",
                          fontFamily: "monospace",
                        }}
                      >
                        {op.end_time - op.start_time}
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
