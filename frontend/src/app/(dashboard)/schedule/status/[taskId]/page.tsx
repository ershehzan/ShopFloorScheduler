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

    let ws: WebSocket | null = null;
    let isMounted = true;
    let pollInterval: NodeJS.Timeout | null = null;

    const startPolling = () => {
      console.log("WS: Falling back to HTTP polling...");
      const poll = async () => {
        try {
          const s = await getStatus(taskId);
          if (!isMounted) return;
          setStatus(s);
          if (s.state === "complete") {
            if (pollInterval) clearInterval(pollInterval);
            setTimeout(() => {
              if (isMounted) router.push(`/schedule/results/${taskId}`);
            }, 800);
          } else if (s.state === "error") {
            if (pollInterval) clearInterval(pollInterval);
          }
        } catch (err) {
          if (!isMounted) return;
          setApiError(err instanceof Error ? err.message : "Failed to fetch status.");
          if (pollInterval) clearInterval(pollInterval);
        }
      };

      poll();
      pollInterval = setInterval(poll, 2000);
    };

    const connectWebSocket = () => {
      try {
        const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
          .replace(/^http/, "ws") + `/api/ws/tasks/${taskId}`;
        
        console.log(`WS: Connecting to ${wsUrl}`);
        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            console.log("WS Received:", data);

            if (data.type === "progress") {
              setStatus((prev) => ({
                ...prev,
                state: "processing",
                message: `Optimizing... Generation ${data.generation}/${data.total_generations} (Best makespan/fitness: ${data.best_fitness})`,
              }));
            } else if (data.type === "complete") {
              setStatus({
                task_id: taskId,
                state: "complete",
                message: "Schedule optimization completed successfully.",
                result: data.result,
              });
              if (ws) ws.close();
              setTimeout(() => {
                if (isMounted) router.push(`/schedule/results/${taskId}`);
              }, 800);
            } else if (data.type === "error") {
              setStatus({
                task_id: taskId,
                state: "error",
                message: data.message || "Optimization failed.",
                result: null,
              });
              if (ws) ws.close();
            }
          } catch (err) {
            console.error("Failed to parse WS payload", err);
          }
        };

        ws.onerror = (err) => {
          console.error("WS connection error:", err);
          if (isMounted) {
            startPolling();
          }
        };

        ws.onclose = (event) => {
          console.log("WebSocket closed with code:", event.code);
          // If closed prematurely (not completed/error state), trigger polling
          if (event.code !== 1000 && isMounted && status.state !== "complete" && status.state !== "error") {
            startPolling();
          }
        };
      } catch (wsSetupErr) {
        console.error("Failed to initialize WebSocket, falling back to HTTP polling:", wsSetupErr);
        startPolling();
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
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
