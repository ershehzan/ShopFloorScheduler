"use client";

import React, { useCallback, useState } from "react";
import { Upload, FileSpreadsheet, X, AlertCircle } from "lucide-react";

interface UploadZoneProps {
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
  error?: string;
}

export default function UploadZone({ onFileSelect, selectedFile, error }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && (file.name.endsWith(".xlsx") || file.name.endsWith(".xls"))) {
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    onFileSelect(file);
  };

  const formatSize = (bytes: number) =>
    bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(1)} KB`
      : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        style={{
          border: `2px dashed ${
            error ? "var(--error)" : dragging ? "var(--secondary)" : "var(--border-strong)"
          }`,
          borderRadius: "var(--radius-lg)",
          padding: 40,
          textAlign: "center",
          background: dragging
            ? "rgba(37,99,235,0.04)"
            : error
            ? "rgba(239,68,68,0.03)"
            : "var(--bg-secondary)",
          transition: "all var(--transition-fast)",
          cursor: "pointer",
          position: "relative",
        }}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept=".xlsx,.xls"
          style={{ display: "none" }}
          onChange={handleChange}
        />

        {selectedFile ? (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: "var(--radius-md)",
                background: "rgba(16,185,129,0.1)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <FileSpreadsheet size={28} style={{ color: "var(--success)" }} />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--text-primary)" }}>
                {selectedFile.name}
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 2 }}>
                {formatSize(selectedFile.size)}
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onFileSelect(null); }}
              className="btn btn-secondary"
              style={{ height: 32, fontSize: "0.8125rem", gap: 6 }}
              id="remove-file-btn"
            >
              <X size={14} />
              Remove
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: "var(--radius-md)",
                background: "rgba(37,99,235,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Upload size={28} style={{ color: "var(--secondary)" }} />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.9375rem", color: "var(--text-primary)" }}>
                Drop your Excel file here
              </div>
              <div style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: 4 }}>
                or <span style={{ color: "var(--secondary)", fontWeight: 500 }}>browse to upload</span>
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 8 }}>
                Supports .xlsx and .xls files
              </div>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginTop: 8,
            color: "var(--error)",
            fontSize: "0.875rem",
          }}
        >
          <AlertCircle size={14} />
          {error}
        </div>
      )}
    </div>
  );
}
