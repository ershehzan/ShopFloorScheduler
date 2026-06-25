"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, AlertCircle } from "lucide-react";
import UploadZone from "@/components/schedule/UploadZone";
import AlgorithmConfig from "@/components/schedule/AlgorithmConfig";
import { uploadSchedule } from "@/lib/api";

const DEFAULT_CONFIG = {
  algorithm: "GA",
  setup_time: 2,
  pop_size: 30,
  generations: 50,
  mutation_rate: 0.1,
  w_makespan: 0.6,
  w_tardiness: 0.4,
};

export default function NewSchedulePage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const handleConfigChange = (field: string, value: string | number) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setFileError("Please select an Excel file before submitting.");
      return;
    }
    setFileError(null);
    setError(null);
    setLoading(true);

    try {
      const res = await uploadSchedule(file, config);
      router.push(`/schedule/status/${res.task_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to start schedule optimization.";
      setError(msg);
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      {/* Page header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>New Schedule</h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
          Upload your job data and configure the optimization parameters.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 380px",
            gap: 24,
            alignItems: "flex-start",
          }}
        >
          {/* Left Column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
            {/* Upload */}
            <div className="card">
              <h2
                style={{
                  fontSize: "1rem",
                  fontWeight: 600,
                  marginBottom: 4,
                }}
              >
                Upload Job Data
              </h2>
              <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: 20 }}>
                Provide an Excel file with <strong>Jobs</strong>, <strong>Operations</strong>, and{" "}
                <strong>Machines</strong> sheets. Download the{" "}
                <a
                  href="/template.xlsx"
                  style={{ color: "var(--secondary)", textDecoration: "none", fontWeight: 500 }}
                >
                  sample template
                </a>{" "}
                to get started.
              </p>
              <UploadZone
                onFileSelect={(f) => {
                  setFile(f);
                  setFileError(null);
                }}
                selectedFile={file}
                error={fileError ?? undefined}
              />
            </div>

            {/* Data format hint */}
            <div
              className="card"
              style={{
                background: "rgba(6,182,212,0.04)",
                borderColor: "rgba(6,182,212,0.25)",
                padding: 16,
              }}
            >
              <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--accent)", marginBottom: 8 }}>
                📋 Expected Excel Format
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 12,
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>Jobs Sheet</div>
                  <div>Job_ID, Due_Date, Priority</div>
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>Operations Sheet</div>
                  <div>Job_ID, Machine_ID, Processing_Time</div>
                </div>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>Machines Sheet</div>
                  <div>Machine_ID (optional maintenance)</div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column — Config */}
          <div
            className="card"
            style={{ position: "sticky", top: "calc(var(--topnav-height) + 32px)" }}
          >
            <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 4 }}>
              Optimization Config
            </h2>
            <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: 24 }}>
              Configure the scheduling algorithm and parameters.
            </p>

            <AlgorithmConfig values={config} onChange={handleConfigChange} />

            <div className="divider" style={{ margin: "24px 0" }} />

            {error && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "12px 14px",
                  background: "rgba(239,68,68,0.06)",
                  border: "1px solid rgba(239,68,68,0.2)",
                  borderRadius: "var(--radius-md)",
                  color: "var(--error)",
                  fontSize: "0.875rem",
                  marginBottom: 16,
                }}
              >
                <AlertCircle size={14} />
                {error}
              </div>
            )}

            <button
              type="submit"
              id="submit-schedule-btn"
              className="btn btn-primary"
              style={{ width: "100%", gap: 8 }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Starting optimization...
                </>
              ) : (
                <>
                  Run Schedule Optimization
                  <ArrowRight size={16} />
                </>
              )}
            </button>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", textAlign: "center", marginTop: 8 }}>
              You'll be redirected to a live status page
            </p>
          </div>
        </div>
      </form>
    </div>
  );
}
