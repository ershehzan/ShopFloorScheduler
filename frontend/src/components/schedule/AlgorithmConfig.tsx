"use client";

import React from "react";

interface AlgorithmConfigProps {
  values: {
    algorithm: string;
    setup_time: number;
    pop_size: number;
    generations: number;
    mutation_rate: number;
    w_makespan: number;
    w_tardiness: number;
  };
  onChange: (field: string, value: string | number) => void;
}

const ALGORITHMS = [
  { value: "GA",   label: "Genetic Algorithm",         desc: "Multi-objective optimization (recommended)" },
  { value: "FCFS", label: "First-Come First-Served",   desc: "Processes jobs in arrival order" },
  { value: "SPT",  label: "Shortest Processing Time",  desc: "Minimizes average flow time" },
  { value: "EDD",  label: "Earliest Due Date",         desc: "Minimizes maximum tardiness" },
  { value: "WSPT", label: "Weighted SPT",              desc: "Priority-weighted variant of SPT" },
];

function SliderField({
  label,
  id,
  value,
  min,
  max,
  step,
  format,
  onChange,
  disabled,
}: {
  label: string;
  id: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <label
          htmlFor={id}
          style={{
            fontSize: "0.875rem",
            fontWeight: 500,
            color: disabled ? "var(--text-muted)" : "var(--text-primary)",
          }}
        >
          {label}
        </label>
        <span
          style={{
            fontSize: "0.875rem",
            fontWeight: 600,
            color: disabled ? "var(--text-muted)" : "var(--secondary)",
            minWidth: 48,
            textAlign: "right",
          }}
        >
          {format(value)}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{
          width: "100%",
          height: 4,
          accentColor: "var(--secondary)",
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.4 : 1,
        }}
      />
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}

export default function AlgorithmConfig({ values, onChange }: AlgorithmConfigProps) {
  const isGA = values.algorithm === "GA";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Algorithm Selection */}
      <div>
        <label
          style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-primary)", display: "block", marginBottom: 10 }}
        >
          Scheduling Algorithm
        </label>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {ALGORITHMS.map(({ value, label, desc }) => (
            <button
              key={value}
              type="button"
              id={`algo-${value.toLowerCase()}`}
              onClick={() => onChange("algorithm", value)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                borderRadius: "var(--radius-md)",
                border: `1px solid ${values.algorithm === value ? "var(--secondary)" : "var(--border)"}`,
                background: values.algorithm === value ? "rgba(37,99,235,0.06)" : "var(--surface)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all var(--transition-fast)",
              }}
            >
              <div
                style={{
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  border: `2px solid ${values.algorithm === value ? "var(--secondary)" : "var(--border-strong)"}`,
                  background: values.algorithm === value ? "var(--secondary)" : "transparent",
                  flexShrink: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {values.algorithm === value && (
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#fff" }} />
                )}
              </div>
              <div>
                <div style={{ fontWeight: 500, fontSize: "0.875rem", color: "var(--text-primary)" }}>
                  {label}
                  {value === "GA" && (
                    <span className="badge badge-info" style={{ marginLeft: 8, fontSize: "0.625rem" }}>
                      Recommended
                    </span>
                  )}
                </div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{desc}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="divider" />

      {/* Setup Time */}
      <SliderField
        label="Setup Time (time units)"
        id="setup-time"
        value={values.setup_time}
        min={0}
        max={30}
        step={1}
        format={(v) => `${v}`}
        onChange={(v) => onChange("setup_time", v)}
      />

      {/* GA-specific parameters */}
      {isGA && (
        <>
          <div className="divider" />
          <div
            style={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Genetic Algorithm Parameters
          </div>
          <SliderField
            label="Population Size"
            id="pop-size"
            value={values.pop_size}
            min={10}
            max={200}
            step={10}
            format={(v) => `${v}`}
            onChange={(v) => onChange("pop_size", v)}
          />
          <SliderField
            label="Generations"
            id="generations"
            value={values.generations}
            min={10}
            max={500}
            step={10}
            format={(v) => `${v}`}
            onChange={(v) => onChange("generations", v)}
          />
          <SliderField
            label="Mutation Rate"
            id="mutation-rate"
            value={values.mutation_rate}
            min={0.01}
            max={0.5}
            step={0.01}
            format={(v) => `${(v * 100).toFixed(0)}%`}
            onChange={(v) => onChange("mutation_rate", v)}
          />
          <SliderField
            label="Makespan Weight"
            id="w-makespan"
            value={values.w_makespan}
            min={0.1}
            max={0.9}
            step={0.1}
            format={(v) => v.toFixed(1)}
            onChange={(v) => {
              onChange("w_makespan", v);
              onChange("w_tardiness", Math.round((1 - v) * 10) / 10);
            }}
          />
          <SliderField
            label="Tardiness Weight"
            id="w-tardiness"
            value={values.w_tardiness}
            min={0.1}
            max={0.9}
            step={0.1}
            format={(v) => v.toFixed(1)}
            onChange={(v) => {
              onChange("w_tardiness", v);
              onChange("w_makespan", Math.round((1 - v) * 10) / 10);
            }}
          />
        </>
      )}
    </div>
  );
}
