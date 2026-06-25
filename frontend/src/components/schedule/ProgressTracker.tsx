"use client";

import React, { useEffect, useRef } from "react";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

export type ScheduleState = "pending" | "processing" | "complete" | "error";

const STEPS = [
  { key: "pending",    label: "Queued",             desc: "Job queued for processing" },
  { key: "processing", label: "Running Algorithm",  desc: "Optimization in progress" },
  { key: "complete",   label: "Complete",            desc: "Schedule generated successfully" },
];

function stepStatus(step: string, current: ScheduleState) {
  const order: ScheduleState[] = ["pending", "processing", "complete"];
  const si = order.indexOf(step as ScheduleState);
  const ci = order.indexOf(current === "error" ? "processing" : current);
  if (current === "error" && step === "complete") return "error";
  if (si < ci) return "done";
  if (si === ci) return "active";
  return "upcoming";
}

interface ProgressTrackerProps {
  state: ScheduleState;
  message: string;
  taskId: string;
}

export default function ProgressTracker({ state, message, taskId }: ProgressTrackerProps) {
  const isComplete = state === "complete";
  const isError = state === "error";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      {/* Steps */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {STEPS.map(({ key, label, desc }, idx) => {
          const status = stepStatus(key, state);
          return (
            <div key={key} style={{ display: "flex", gap: 16 }}>
              {/* Icon + line */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background:
                      status === "done"
                        ? "var(--success)"
                        : status === "active"
                        ? "var(--secondary)"
                        : status === "error"
                        ? "var(--error)"
                        : "var(--bg-secondary)",
                    border: `2px solid ${
                      status === "done"
                        ? "var(--success)"
                        : status === "active"
                        ? "var(--secondary)"
                        : status === "error"
                        ? "var(--error)"
                        : "var(--border)"
                    }`,
                    transition: "all var(--transition-base)",
                    flexShrink: 0,
                  }}
                >
                  {status === "done" && <CheckCircle2 size={18} color="#fff" />}
                  {status === "active" && <Loader2 size={18} color="#fff" className="animate-spin" />}
                  {status === "error" && <XCircle size={18} color="#fff" />}
                  {status === "upcoming" && <Circle size={18} color="var(--text-muted)" />}
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    style={{
                      width: 2,
                      flex: 1,
                      minHeight: 32,
                      background:
                        status === "done" ? "var(--success)" : "var(--border)",
                      margin: "4px 0",
                      transition: "background var(--transition-slow)",
                    }}
                  />
                )}
              </div>

              {/* Content */}
              <div style={{ paddingTop: 6, paddingBottom: idx < STEPS.length - 1 ? 24 : 0 }}>
                <div
                  style={{
                    fontWeight: status === "active" ? 600 : 500,
                    fontSize: "0.9375rem",
                    color:
                      status === "done"
                        ? "var(--success)"
                        : status === "active"
                        ? "var(--text-primary)"
                        : status === "error"
                        ? "var(--error)"
                        : "var(--text-muted)",
                  }}
                >
                  {label}
                </div>
                <div style={{ fontSize: "0.875rem", color: "var(--text-muted)", marginTop: 2 }}>
                  {status === "active" ? message || desc : desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Task ID */}
      <div
        style={{
          padding: "10px 14px",
          background: "var(--bg-secondary)",
          borderRadius: "var(--radius-md)",
          fontSize: "0.8125rem",
          color: "var(--text-muted)",
          fontFamily: "monospace",
        }}
      >
        Task ID: {taskId}
      </div>
    </div>
  );
}
