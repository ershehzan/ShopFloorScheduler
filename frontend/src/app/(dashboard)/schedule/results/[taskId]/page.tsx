"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, RefreshCw, Loader2 } from "lucide-react";
import KPICards from "@/components/results/KPICards";
import ExportButtons from "@/components/results/ExportButtons";
import GanttChart from "@/components/gantt/GanttChart";
import { getResults, StatusResponse } from "@/lib/api";

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
