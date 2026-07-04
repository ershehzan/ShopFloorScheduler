"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Activity,
  Clock,
  Cpu,
  TrendingUp,
  Plus,
  ChevronRight,
  Loader2,
  CheckCircle2,
  XCircle,
  Eye,
} from "lucide-react";
import {
  getAnalyticsSummary,
  getHistory,
  AnalyticsSummaryData,
  ScheduleRunSummary,
} from "@/lib/api";

// ── Status badge helper ────────────────────────────────────────────────────
function StatusBadge({ status }: { status: ScheduleRunSummary["status"] }) {
  const map = {
    pending: {
      icon: <Clock size={12} />,
      label: "Pending",
      cls: "badge-warning",
    },
    processing: {
      icon: <Loader2 size={12} className="animate-spin" />,
      label: "Processing",
      cls: "badge-info",
    },
    complete: {
      icon: <CheckCircle2 size={12} />,
      label: "Complete",
      cls: "badge-success",
    },
    error: {
      icon: <XCircle size={12} />,
      label: "Error",
      cls: "badge-error",
    },
  };
  const { icon, label, cls } = map[status] ?? map.pending;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}
    >
      {icon}
      {label}
    </span>
  );
}

// ── Algorithm badge ────────────────────────────────────────────────────────
const ALGO_COLORS: Record<string, string> = {
  GA: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  FCFS: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  SPT: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
  EDD: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  WSPT: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300",
};

function AlgoBadge({ algo }: { algo: string | null }) {
  if (!algo) return <span className="text-muted">—</span>;
  const cls =
    ALGO_COLORS[algo.toUpperCase()] ??
    "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {algo}
    </span>
  );
}

// ── Metric cell ────────────────────────────────────────────────────────────
function Metric({ value, unit = "" }: { value: number | null; unit?: string }) {
  if (value === null || value === undefined)
    return <span className="text-muted">—</span>;
  return (
    <span className="font-mono text-sm">
      {value.toFixed(1)}
      {unit && <span className="text-xs text-muted ml-0.5">{unit}</span>}
    </span>
  );
}

export default function DashboardClient() {
  const [summary, setSummary] = useState<AnalyticsSummaryData | null>(null);
  const [recentRuns, setRecentRuns] = useState<ScheduleRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    await Promise.resolve();
    setLoading(true);
    setError("");
    try {
      const [sumData, histData] = await Promise.all([
        getAnalyticsSummary(),
        getHistory({ page: 1, page_size: 5 }),
      ]);
      setSummary(sumData);
      setRecentRuns(histData.items);
    } catch (err: unknown) {
      console.error("Dashboard error:", err);
      setError(err instanceof Error ? err.message : "Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      loadData();
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: 400,
        }}
      >
        <Loader2 size={36} className="animate-spin text-accent" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="card"
        style={{
          maxWidth: 600,
          margin: "40px auto",
          textAlign: "center",
          borderColor: "rgba(239, 68, 68, 0.2)",
          background: "rgba(239, 68, 68, 0.02)",
        }}
      >
        <h3 style={{ color: "var(--error)", marginBottom: 8, fontSize: "1.125rem", fontWeight: 600 }}>
          Error Loading Dashboard
        </h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: 20 }}>
          {error}
        </p>
        <button className="btn btn-primary" onClick={loadData}>
          Retry
        </button>
      </div>
    );
  }

  const totalRuns = summary?.total_runs || 0;

  const cards = [
    {
      label: "Avg Makespan",
      value: totalRuns > 0 ? summary!.avg_makespan.toFixed(1) : "—",
      unit: "time units",
      icon: Clock,
      accent: "kpi-card-blue",
    },
    {
      label: "Machine Utilization",
      value: totalRuns > 0 ? `${(summary!.avg_utilization * 100).toFixed(1)}%` : "—",
      unit: "%",
      icon: Cpu,
      accent: "kpi-card-cyan",
    },
    {
      label: "On-Time Delivery",
      value: totalRuns > 0 ? `${summary!.avg_on_time_percent.toFixed(1)}%` : "—",
      unit: "%",
      icon: TrendingUp,
      accent: "kpi-card-green",
    },
    {
      label: "Total Runs",
      value: totalRuns.toString(),
      unit: "schedules",
      icon: Activity,
      accent: "kpi-card-amber",
    },
  ];

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
          <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Dashboard</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
            Monitor your production scheduling operations and performance metrics.
          </p>
        </div>
        <Link
          href="/schedule/new"
          className="btn btn-primary"
          id="new-schedule-btn"
          style={{ gap: 8 }}
        >
          <Plus size={16} />
          New Schedule
        </Link>
      </div>

      {/* KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 20,
          marginBottom: 32,
        }}
      >
        {cards.map(({ label, value, unit, icon: Icon, accent }) => (
          <div key={label} className={`card ${accent}`} style={{ padding: 20 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 16,
              }}
            >
              <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                {label}
              </span>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon size={16} style={{ color: "var(--text-secondary)" }} />
              </div>
            </div>
            <div
              style={{
                fontSize: "1.75rem",
                fontWeight: 700,
                color: "var(--text-primary)",
                lineHeight: 1,
                marginBottom: 4,
              }}
            >
              {value}
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{unit}</div>
          </div>
        ))}
      </div>

      {/* Two-column: Quick Actions + Getting Started */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          marginBottom: 32,
        }}
      >
        {/* Quick Actions */}
        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Quick Actions</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { href: "/schedule/new", label: "Upload Job Data & Schedule", desc: "Start a new optimization run", color: "var(--secondary)" },
              { href: "/reports", label: "Download Reports", desc: "PDF, Excel, and CSV exports", color: "var(--accent)" },
              { href: "/analytics", label: "View Analytics", desc: "Trend charts and utilization", color: "var(--success)" },
            ].map(({ href, label, desc, color }) => (
              <Link
                key={href}
                href={href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  textDecoration: "none",
                  color: "var(--text-primary)",
                  transition: "all var(--transition-fast)",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: color,
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{label}</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{desc}</div>
                  </div>
                </div>
                <ChevronRight size={16} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
              </Link>
            ))}
          </div>
        </div>

        {/* Getting Started */}
        <div
          className="card"
          style={{
            background: "linear-gradient(135deg, rgba(30,64,175,0.06), rgba(6,182,212,0.06))",
            borderColor: "rgba(37,99,235,0.2)",
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 8 }}>
            Getting Started
          </h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: 20, lineHeight: 1.6 }}>
            Upload your Excel job data, configure the optimization algorithm, and generate
            a Gantt chart schedule in seconds.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[
              "1. Prepare an Excel file with Jobs, Operations, and Machines sheets",
              "2. Click \"New Schedule\" and upload your file",
              "3. Choose algorithm (GA, FCFS, SPT, EDD, or WSPT)",
              "4. View the Gantt chart and download your report",
            ].map((step) => (
              <div
                key={step}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                <span style={{ color: "var(--secondary)", fontWeight: 600, flexShrink: 0 }}>→</span>
                {step}
              </div>
            ))}
          </div>
          <Link
            href="/schedule/new"
            className="btn btn-primary"
            style={{ marginTop: 20, width: "100%" }}
            id="dashboard-get-started-btn"
          >
            Start Scheduling
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Recent Schedule Runs</h3>
          {recentRuns.length > 0 && (
            <Link
              href="/history"
              style={{ fontSize: "0.8125rem", color: "var(--secondary)", textDecoration: "none", fontWeight: 500 }}
            >
              View all
            </Link>
          )}
        </div>

        {recentRuns.length === 0 ? (
          <div
            style={{
              textAlign: "center",
              padding: "48px 24px",
              color: "var(--text-muted)",
            }}
          >
            <Activity size={40} style={{ marginBottom: 12, opacity: 0.4 }} />
            <p style={{ fontWeight: 500, marginBottom: 4 }}>No schedule runs yet</p>
            <p style={{ fontSize: "0.875rem" }}>
              Create your first schedule to see results here.
            </p>
            <Link
              href="/schedule/new"
              className="btn btn-primary"
              style={{ marginTop: 16, display: "inline-flex" }}
            >
              <Plus size={16} />
              Create Schedule
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-2">
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">Date</th>
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">File</th>
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">Algorithm</th>
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">Makespan</th>
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">Tardiness</th>
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">On-Time %</th>
                  <th className="px-4 py-3 text-left font-semibold text-secondary-text">Status</th>
                  <th className="px-4 py-3 text-right font-semibold text-secondary-text">Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run, i) => (
                  <tr
                    key={run.task_id}
                    className={`border-b border-border hover:bg-surface-2 transition-colors ${
                      i % 2 === 0 ? "" : "bg-surface-2/40"
                    }`}
                  >
                    <td className="px-4 py-3 text-secondary-text whitespace-nowrap">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 max-w-[160px] truncate" title={run.file_name ?? ""}>
                      {run.file_name ? (
                        <span className="font-medium text-primary-text">{run.file_name}</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <AlgoBadge algo={run.algorithm} />
                    </td>
                    <td className="px-4 py-3">
                      <Metric value={run.makespan} unit="min" />
                    </td>
                    <td className="px-4 py-3">
                      <Metric value={run.total_tardiness} />
                    </td>
                    <td className="px-4 py-3">
                      <Metric value={run.on_time_percent} unit="%" />
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={run.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      {run.status === "complete" ? (
                        <Link
                          href={`/schedule/results/${run.task_id}`}
                          className="btn btn-ghost btn-sm inline-flex items-center gap-1"
                          id={`dashboard-view-run-${i}`}
                        >
                          <Eye size={14} />
                          View
                        </Link>
                      ) : (
                        <span className="text-muted text-xs">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
