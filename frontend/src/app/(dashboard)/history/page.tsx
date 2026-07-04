"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { getHistory, ScheduleRunSummary } from "@/lib/api";

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

// ── Main page ─────────────────────────────────────────────────────────────

const ALGORITHMS = ["", "GA", "FCFS", "SPT", "EDD", "WSPT"];
const STATUSES = ["", "pending", "processing", "complete", "error"];

export default function HistoryPage() {
  const [runs, setRuns] = useState<ScheduleRunSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const PAGE_SIZE = 10;

  const [algorithm, setAlgorithm] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    await Promise.resolve();
    setLoading(true);
    setError(null);
    try {
      const data = await getHistory({
        page,
        page_size: PAGE_SIZE,
        ...(algorithm ? { algorithm } : {}),
        ...(status ? { status } : {}),
      });
      setRuns(data.items);
      setTotal(data.total);
      setPages(data.pages);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to fetch history");
    } finally {
      setLoading(false);
    }
  }, [page, algorithm, status]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchHistory();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchHistory]);

  // Reset to page 1 when filters change
  const handleFilter = (newAlgo: string, newStatus: string) => {
    setPage(1);
    setAlgorithm(newAlgo);
    setStatus(newStatus);
  };

  // Client-side search filter on task_id / file_name
  const filtered = search.trim()
    ? runs.filter(
        (r) =>
          r.task_id.toLowerCase().includes(search.toLowerCase()) ||
          (r.file_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : runs;

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary-text">
            Schedule History
          </h1>
          <p className="text-secondary-text text-sm mt-1">
            {total} run{total !== 1 ? "s" : ""} recorded
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            id="history-refresh-btn"
            onClick={fetchHistory}
            className="btn btn-ghost"
            title="Refresh"
          >
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
          <Link href="/schedule/new" className="btn btn-primary">
            <Plus size={16} />
            New Schedule
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-center">
          {/* Search */}
          <div className="relative flex-1 min-w-[200px]">
            <Search
              size={15}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              id="history-search"
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by task ID or filename…"
              className="form-input pl-9 h-9 text-sm w-full"
            />
          </div>

          {/* Algorithm filter */}
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={15} className="text-muted" />
            <select
              id="history-algo-filter"
              value={algorithm}
              onChange={(e) => handleFilter(e.target.value, status)}
              className="form-input h-9 text-sm pr-8"
            >
              <option value="">All Algorithms</option>
              {ALGORITHMS.slice(1).map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>

          {/* Status filter */}
          <select
            id="history-status-filter"
            value={status}
            onChange={(e) => handleFilter(algorithm, e.target.value)}
            className="form-input h-9 text-sm pr-8"
          >
            <option value="">All Statuses</option>
            {STATUSES.slice(1).map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error">
          <XCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2">
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  Date
                </th>
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  File
                </th>
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  Algorithm
                </th>
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  Makespan
                </th>
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  Tardiness
                </th>
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  On-Time %
                </th>
                <th className="px-4 py-3 text-left font-semibold text-secondary-text">
                  Status
                </th>
                <th className="px-4 py-3 text-right font-semibold text-secondary-text">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center gap-3 text-secondary-text">
                      <Loader2 size={28} className="animate-spin text-accent" />
                      <span>Loading history…</span>
                    </div>
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center gap-3 text-secondary-text">
                      <Clock size={36} className="opacity-30" />
                      <p className="font-medium">No runs found</p>
                      <p className="text-sm">
                        {total === 0
                          ? "Upload your first schedule to get started."
                          : "Try adjusting your filters."}
                      </p>
                      {total === 0 && (
                        <Link href="/schedule/new" className="btn btn-primary mt-2">
                          <Plus size={14} /> New Schedule
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              )}
              {!loading &&
                filtered.map((run, i) => (
                  <tr
                    key={run.task_id}
                    className={`border-b border-border hover:bg-surface-2 transition-colors ${
                      i % 2 === 0 ? "" : "bg-surface-2/40"
                    }`}
                  >
                    {/* Date */}
                    <td className="px-4 py-3 text-secondary-text whitespace-nowrap">
                      {new Date(run.created_at).toLocaleString()}
                    </td>

                    {/* File */}
                    <td className="px-4 py-3 max-w-[160px] truncate" title={run.file_name ?? ""}>
                      {run.file_name ? (
                        <span className="font-medium text-primary-text">{run.file_name}</span>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>

                    {/* Algorithm */}
                    <td className="px-4 py-3">
                      <AlgoBadge algo={run.algorithm} />
                    </td>

                    {/* Makespan */}
                    <td className="px-4 py-3">
                      <Metric value={run.makespan} unit="min" />
                    </td>

                    {/* Tardiness */}
                    <td className="px-4 py-3">
                      <Metric value={run.total_tardiness} />
                    </td>

                    {/* On-time % */}
                    <td className="px-4 py-3">
                      <Metric value={run.on_time_percent} unit="%" />
                    </td>

                    {/* Status */}
                    <td className="px-4 py-3">
                      <StatusBadge status={run.status} />
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      {run.status === "complete" ? (
                        <Link
                          href={`/schedule/results/${run.task_id}`}
                          className="btn btn-ghost btn-sm inline-flex items-center gap-1"
                          id={`view-run-${i}`}
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

        {/* Pagination */}
        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <span className="text-sm text-secondary-text">
              Page {page} of {pages} &middot; {total} total
            </span>
            <div className="flex items-center gap-2">
              <button
                id="history-prev-page"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-ghost btn-sm"
              >
                <ChevronLeft size={16} />
                Prev
              </button>
              <button
                id="history-next-page"
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                disabled={page === pages}
                className="btn btn-ghost btn-sm"
              >
                Next
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
