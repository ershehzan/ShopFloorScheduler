"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileText,
  Download,
  Loader2,
  Eye,
} from "lucide-react";
import { getHistory, ScheduleRunSummary, resourceUrl } from "@/lib/api";

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

export default function ReportsClient() {
  const [runs, setRuns] = useState<ScheduleRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    await Promise.resolve();
    setLoading(true);
    setError("");
    try {
      const data = await getHistory({ status: "complete", page_size: 100 });
      setRuns(data.items);
    } catch (err: unknown) {
      console.error("Reports error:", err);
      setError(err instanceof Error ? err.message : "Failed to load reports.");
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
          Error Loading Reports
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

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Reports</h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Download schedule reports in PDF, Excel, and CSV formats.
        </p>
      </div>

      {runs.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 60 }}>
          <FileText size={48} style={{ color: "var(--text-muted)", opacity: 0.4, marginBottom: 16 }} />
          <h3 style={{ fontSize: "1.125rem", marginBottom: 8 }}>No reports yet</h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem", marginBottom: 20 }}>
            Complete a schedule run to generate downloadable reports.
          </p>
          <Link href="/schedule/new" className="btn btn-primary" id="reports-new-schedule-btn">
            <Download size={16} />
            Create Your First Schedule
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden p-0">
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
                  <th className="px-4 py-3 text-right font-semibold text-secondary-text">Actions</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run, i) => {
                  const downloadUrl = resourceUrl(`/api/schedule/download/schedule_${run.task_id}.xlsx`);
                  return (
                    <tr
                      key={run.task_id}
                      className={`border-b border-border hover:bg-surface-2 transition-colors ${
                        i % 2 === 0 ? "" : "bg-surface-2/40"
                      }`}
                    >
                      <td className="px-4 py-3 text-secondary-text whitespace-nowrap">
                        {new Date(run.created_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 max-w-[200px] truncate" title={run.file_name ?? ""}>
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
                      <td className="px-4 py-3 text-right">
                        <div style={{ display: "inline-flex", gap: 8, justifyContent: "flex-end" }}>
                          {downloadUrl && (
                            <a
                              id={`download-report-${i}`}
                              href={downloadUrl}
                              download
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn btn-secondary btn-sm"
                              style={{ gap: 6 }}
                            >
                              <Download size={12} />
                              Download Excel
                            </a>
                          )}
                          <Link
                            href={`/schedule/results/${run.task_id}`}
                            className="btn btn-ghost btn-sm inline-flex items-center gap-1"
                            id={`view-report-${i}`}
                          >
                            <Eye size={12} />
                            View
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
