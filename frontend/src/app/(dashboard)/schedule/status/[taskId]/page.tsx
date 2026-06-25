"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowLeft } from "lucide-react";
import ProgressTracker, { ScheduleState } from "@/components/schedule/ProgressTracker";
import { getStatus, StatusResponse } from "@/lib/api";

export default function StatusPage({ params }: { params: Promise<{ taskId: string }> }) {
  const router = useRouter();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<StatusResponse>({
    task_id: "",
    state: "pending",
    message: "Waiting to start...",
    result: null,
  });
  const [apiError, setApiError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Resolve async params
  useEffect(() => {
    params.then((p) => setTaskId(p.taskId));
  }, [params]);

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const s = await getStatus(taskId);
        setStatus(s);
        if (s.state === "complete") {
          clearInterval(intervalRef.current!);
          setTimeout(() => router.push(`/schedule/results/${taskId}`), 800);
        } else if (s.state === "error") {
          clearInterval(intervalRef.current!);
        }
      } catch (err) {
        setApiError(err instanceof Error ? err.message : "Failed to fetch status.");
        clearInterval(intervalRef.current!);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => clearInterval(intervalRef.current!);
  }, [taskId, router]);

  return (
    <div className="animate-fade-in" style={{ maxWidth: 640, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <button
          onClick={() => router.push("/schedule/new")}
          className="btn btn-ghost"
          style={{ height: 32, fontSize: "0.875rem", gap: 6, marginBottom: 16, padding: "0 8px" }}
        >
          <ArrowLeft size={14} />
          Back
        </button>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Optimization Status</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
          Your schedule is being optimized. This may take a few moments.
        </p>
      </div>

      {/* Status card */}
      <div className="card">
        <ProgressTracker
          state={status.state as ScheduleState}
          message={status.message}
          taskId={taskId ?? "—"}
        />

        {status.state === "complete" && (
          <div
            style={{
              marginTop: 24,
              padding: "14px 16px",
              background: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.25)",
              borderRadius: "var(--radius-md)",
              color: "var(--success)",
              fontSize: "0.875rem",
              fontWeight: 500,
            }}
          >
            ✓ Optimization complete! Redirecting to results...
          </div>
        )}

        {status.state === "error" && (
          <div
            style={{
              marginTop: 24,
              padding: "14px 16px",
              background: "rgba(239,68,68,0.06)",
              border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: "var(--radius-md)",
              color: "var(--error)",
              fontSize: "0.875rem",
              display: "flex",
              gap: 8,
              alignItems: "flex-start",
            }}
          >
            <AlertCircle size={14} style={{ marginTop: 1, flexShrink: 0 }} />
            <div>
              <div style={{ fontWeight: 600 }}>Optimization failed</div>
              <div>{status.message}</div>
            </div>
          </div>
        )}

        {apiError && (
          <div
            style={{
              marginTop: 24,
              padding: "14px 16px",
              background: "rgba(239,68,68,0.06)",
              border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: "var(--radius-md)",
              color: "var(--error)",
              fontSize: "0.875rem",
            }}
          >
            <div style={{ fontWeight: 600 }}>Connection error</div>
            <div>{apiError}</div>
            <div style={{ marginTop: 4, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              Make sure the FastAPI backend is running on http://localhost:8000
            </div>
          </div>
        )}
      </div>

      {/* Tips */}
      <div
        className="card"
        style={{
          marginTop: 20,
          background: "transparent",
          border: "1px solid var(--border)",
          boxShadow: "none",
          padding: 16,
        }}
      >
        <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 8 }}>
          While you wait...
        </div>
        {[
          "Genetic Algorithm: typically takes 10–60 seconds depending on problem size",
          "FCFS/SPT/EDD/WSPT: completes in under 5 seconds",
          "Results include a Gantt chart, KPI metrics, and an Excel download",
        ].map((tip) => (
          <div
            key={tip}
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 6,
              fontSize: "0.8125rem",
              color: "var(--text-secondary)",
            }}
          >
            <span style={{ color: "var(--accent)", flexShrink: 0 }}>•</span>
            {tip}
          </div>
        ))}
      </div>
    </div>
  );
}
