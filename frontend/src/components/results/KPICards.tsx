"use client";

import React from "react";
import { Clock, Activity, TrendingUp, Cpu, CheckCircle2 } from "lucide-react";

interface KPICardsProps {
  makespan: number;
  totalTardiness: number;
  avgFlowTime: number;
  onTimePercent: number;
  algorithm: string;
}

const CARDS = (props: KPICardsProps) => [
  {
    label: "Makespan",
    value: props.makespan.toLocaleString(),
    unit: "time units",
    icon: Clock,
    accent: "kpi-card-blue",
    desc: "Total schedule duration",
  },
  {
    label: "Total Tardiness",
    value: props.totalTardiness.toLocaleString(),
    unit: "time units",
    icon: Activity,
    accent: props.totalTardiness === 0 ? "kpi-card-green" : "kpi-card-amber",
    desc: props.totalTardiness === 0 ? "All jobs on time! 🎉" : "Sum of late completions",
  },
  {
    label: "Avg Flow Time",
    value: props.avgFlowTime.toFixed(1),
    unit: "time units",
    icon: TrendingUp,
    accent: "kpi-card-cyan",
    desc: "Average job completion time",
  },
  {
    label: "On-Time Delivery",
    value: `${props.onTimePercent.toFixed(0)}%`,
    unit: "of jobs",
    icon: CheckCircle2,
    accent: props.onTimePercent >= 90 ? "kpi-card-green" : props.onTimePercent >= 70 ? "kpi-card-amber" : "kpi-card-blue",
    desc: "Jobs delivered by due date",
  },
];

export default function KPICards(props: KPICardsProps) {
  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 16,
        }}
      >
        <Cpu size={16} style={{ color: "var(--text-muted)" }} />
        <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Algorithm:{" "}
          <strong style={{ color: "var(--secondary)" }}>{props.algorithm}</strong>
        </span>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
        }}
      >
        {CARDS(props).map(({ label, value, unit, icon: Icon, accent, desc }) => (
          <div key={label} className={`card ${accent}`} style={{ padding: 18 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 12,
              }}
            >
              <span
                style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}
              >
                {label}
              </span>
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon size={14} style={{ color: "var(--text-secondary)" }} />
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
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{unit}</div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                marginTop: 6,
                borderTop: "1px solid var(--border)",
                paddingTop: 6,
              }}
            >
              {desc}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
