"use client";

import React, { useMemo, useState } from "react";
import { ScheduledOperation } from "@/lib/api";

const JOB_COLORS = [
  "#2563EB", "#06B6D4", "#10B981", "#F59E0B", "#EF4444",
  "#8B5CF6", "#EC4899", "#14B8A6", "#F97316", "#6366F1",
  "#84CC16", "#0EA5E9", "#A855F7", "#22C55E", "#EAB308",
];

function jobColor(jobId: number) {
  return JOB_COLORS[(jobId - 1) % JOB_COLORS.length];
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  jobId: number;
  machine: number;
  start: number;
  end: number;
  opIndex: number;
}

interface GanttChartProps {
  schedule: ScheduledOperation[];
  makespan: number;
}

export default function GanttChart({ schedule, makespan }: GanttChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState>({ visible: false, x: 0, y: 0, jobId: 0, machine: 0, start: 0, end: 0, opIndex: 0 });
  const [zoom, setZoom] = useState(1);

  const machines = useMemo(
    () => [...new Set(schedule.map((op) => op.machine_id))].sort((a, b) => a - b),
    [schedule]
  );

  const jobs = useMemo(
    () => [...new Set(schedule.map((op) => op.job_id))].sort((a, b) => a - b),
    [schedule]
  );

  const rowHeight = 44;
  const labelWidth = 80;
  const chartWidth = 900 * zoom;
  const unitWidth = makespan > 0 ? chartWidth / makespan : 1;
  const totalHeight = machines.length * rowHeight;

  // Axis ticks
  const tickCount = Math.min(10, makespan);
  const tickStep = Math.ceil(makespan / tickCount);
  const ticks = Array.from({ length: Math.floor(makespan / tickStep) + 1 }, (_, i) => i * tickStep);

  return (
    <div>
      {/* Zoom controls */}
      <div style={{ display: "flex", gap: 8, marginBottom: 12, alignItems: "center" }}>
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", fontWeight: 500 }}>Zoom:</span>
        {[0.5, 1, 1.5, 2].map((z) => (
          <button
            key={z}
            id={`zoom-${z}x`}
            onClick={() => setZoom(z)}
            className={`btn ${zoom === z ? "btn-primary" : "btn-secondary"}`}
            style={{ height: 28, padding: "0 12px", fontSize: "0.75rem" }}
          >
            {z}×
          </button>
        ))}
      </div>

      <div style={{ overflowX: "auto", position: "relative" }}>
        <div style={{ minWidth: labelWidth + chartWidth + 16 }}>
          {/* Time axis */}
          <div style={{ display: "flex", marginLeft: labelWidth, marginBottom: 4 }}>
            <div style={{ position: "relative", width: chartWidth, height: 20 }}>
              {ticks.map((t) => (
                <div
                  key={t}
                  style={{
                    position: "absolute",
                    left: t * unitWidth,
                    top: 0,
                    transform: "translateX(-50%)",
                    fontSize: "0.6875rem",
                    color: "var(--text-muted)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {t}
                </div>
              ))}
            </div>
          </div>

          {/* Grid + Bars */}
          <div style={{ display: "flex" }}>
            {/* Machine labels */}
            <div style={{ width: labelWidth, flexShrink: 0 }}>
              {machines.map((m) => (
                <div
                  key={m}
                  style={{
                    height: rowHeight,
                    display: "flex",
                    alignItems: "center",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    paddingRight: 12,
                  }}
                >
                  M{m}
                </div>
              ))}
            </div>

            {/* Chart area */}
            <div
              style={{
                position: "relative",
                width: chartWidth,
                height: totalHeight,
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-sm)",
                overflow: "hidden",
                border: "1px solid var(--border)",
              }}
            >
              {/* Grid lines */}
              {machines.map((_, i) => (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    top: i * rowHeight,
                    left: 0,
                    right: 0,
                    height: 1,
                    background: "var(--border)",
                  }}
                />
              ))}
              {ticks.map((t) => (
                <div
                  key={t}
                  style={{
                    position: "absolute",
                    left: t * unitWidth,
                    top: 0,
                    bottom: 0,
                    width: 1,
                    background: "rgba(0,0,0,0.06)",
                  }}
                />
              ))}

              {/* Operation bars */}
              {schedule.map((op, idx) => {
                const mIdx = machines.indexOf(op.machine_id);
                const x = op.start_time * unitWidth;
                const w = Math.max((op.end_time - op.start_time) * unitWidth - 2, 4);
                const color = jobColor(op.job_id);
                return (
                  <div
                    key={idx}
                    onMouseEnter={(e) =>
                      setTooltip({
                        visible: true,
                        x: e.nativeEvent.offsetX,
                        y: mIdx * rowHeight,
                        jobId: op.job_id,
                        machine: op.machine_id,
                        start: op.start_time,
                        end: op.end_time,
                        opIndex: op.op_index,
                      })
                    }
                    onMouseLeave={() => setTooltip((t) => ({ ...t, visible: false }))}
                    style={{
                      position: "absolute",
                      left: x,
                      top: mIdx * rowHeight + 6,
                      width: w,
                      height: rowHeight - 12,
                      background: color,
                      borderRadius: 4,
                      opacity: 0.88,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      transition: "opacity var(--transition-fast)",
                      overflow: "hidden",
                    }}
                  >
                    {w > 30 && (
                      <span style={{ fontSize: "0.6875rem", color: "#fff", fontWeight: 700, pointerEvents: "none" }}>
                        J{op.job_id}
                      </span>
                    )}
                  </div>
                );
              })}

              {/* Tooltip */}
              {tooltip.visible && (
                <div
                  style={{
                    position: "absolute",
                    top: tooltip.y,
                    left: Math.min(tooltip.x + 12, chartWidth - 160),
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "var(--radius-md)",
                    padding: "10px 14px",
                    boxShadow: "var(--shadow-lg)",
                    fontSize: "0.8125rem",
                    zIndex: 99,
                    pointerEvents: "none",
                    minWidth: 140,
                  }}
                >
                  <div style={{ fontWeight: 700, color: jobColor(tooltip.jobId), marginBottom: 4 }}>
                    Job {tooltip.jobId}
                  </div>
                  <div style={{ color: "var(--text-secondary)" }}>
                    <div>Machine: <strong style={{ color: "var(--text-primary)" }}>M{tooltip.machine}</strong></div>
                    <div>Op Index: <strong style={{ color: "var(--text-primary)" }}>{tooltip.opIndex}</strong></div>
                    <div>Start: <strong style={{ color: "var(--text-primary)" }}>{tooltip.start}</strong></div>
                    <div>End: <strong style={{ color: "var(--text-primary)" }}>{tooltip.end}</strong></div>
                    <div>Duration: <strong style={{ color: "var(--text-primary)" }}>{tooltip.end - tooltip.start}</strong></div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 16 }}>
        {jobs.map((jId) => (
          <div
            key={jId}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: "0.75rem",
              color: "var(--text-secondary)",
              padding: "4px 10px",
              borderRadius: 99,
              background: "var(--bg-secondary)",
              border: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: 2,
                background: jobColor(jId),
              }}
            />
            Job {jId}
          </div>
        ))}
      </div>
    </div>
  );
}
