"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Clock,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  X,
  Check,
  AlertTriangle,
  Filter,
} from "lucide-react";
import {
  getShifts,
  createShift,
  updateShift,
  deleteShift,
  MachineShift,
  MachineShiftIn,
} from "@/lib/api";

// ── Shift name badge ────────────────────────────────────────────────────────
const SHIFT_COLORS: Record<string, string> = {
  MORNING: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  AFTERNOON: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
  NIGHT: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
  DAY: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300",
  EVENING: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300",
};

function ShiftBadge({ name }: { name: string }) {
  const cls =
    SHIFT_COLORS[name.toUpperCase()] ??
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase ${cls}`}>
      {name}
    </span>
  );
}

// ── Empty form state ────────────────────────────────────────────────────────
const EMPTY_FORM: MachineShiftIn = {
  machine_id: "",
  shift_name: "MORNING",
  shift_start: 6,
  shift_end: 14,
  cycle_length: 24,
  is_active: true,
};

// ── Modal ───────────────────────────────────────────────────────────────────
interface ModalProps {
  isOpen: boolean;
  title: string;
  onClose: () => void;
  onSubmit: (form: MachineShiftIn) => Promise<void>;
  initial?: MachineShiftIn;
  saving: boolean;
}

function ShiftModal({ isOpen, title, onClose, onSubmit, initial, saving }: ModalProps) {
  const [form, setForm] = useState<MachineShiftIn>(initial ?? EMPTY_FORM);
  const [err, setErr] = useState("");
  const firstRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setForm(initial ?? EMPTY_FORM);
      setErr("");
      setTimeout(() => firstRef.current?.focus(), 80);
    }
  }, [isOpen, initial]);

  const set = (field: keyof MachineShiftIn, value: string | number | boolean) =>
    setForm((f) => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    if (!form.machine_id.trim()) {
      setErr("Machine ID is required.");
      return;
    }
    try {
      await onSubmit(form);
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Save failed.");
    }
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        backdropFilter: "blur(4px)",
        animation: "fadeIn 0.15s ease",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: 520,
          margin: "0 16px",
          animation: "slideUp 0.18s ease",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 24,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: "linear-gradient(135deg, #10b981, #059669)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Clock size={18} color="#fff" />
            </div>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 700 }}>{title}</h2>
          </div>
          <button
            className="btn btn-ghost"
            onClick={onClose}
            style={{ width: 32, height: 32, padding: 0 }}
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Machine ID */}
          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 6 }}>
              Machine ID <span style={{ color: "var(--error)" }}>*</span>
            </label>
            <input
              ref={firstRef}
              id="shift-machine-id"
              className="input"
              value={form.machine_id}
              onChange={(e) => set("machine_id", e.target.value)}
              placeholder="e.g. M1, M2, CNC-3"
              required
            />
          </div>

          {/* Shift Name */}
          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 6 }}>
              Shift Name
            </label>
            <select
              id="shift-name"
              className="input"
              value={form.shift_name}
              onChange={(e) => set("shift_name", e.target.value)}
              style={{ cursor: "pointer" }}
            >
              {["MORNING", "AFTERNOON", "EVENING", "NIGHT", "DAY", "CUSTOM"].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 6 }}>
                Shift Start (time units)
              </label>
              <input
                id="shift-start"
                className="input"
                type="number"
                min={0}
                step={0.5}
                value={form.shift_start}
                onChange={(e) => set("shift_start", parseFloat(e.target.value) || 0)}
              />
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4 }}>e.g. 6 = 6 h into cycle</p>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 6 }}>
                Shift End (time units)
              </label>
              <input
                id="shift-end"
                className="input"
                type="number"
                min={0}
                step={0.5}
                value={form.shift_end}
                onChange={(e) => set("shift_end", parseFloat(e.target.value) || 0)}
              />
              <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4 }}>e.g. 14 = 14 h into cycle</p>
            </div>
          </div>

          {/* Cycle length */}
          <div>
            <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 6 }}>
              Cycle Length (time units)
            </label>
            <input
              id="shift-cycle"
              className="input"
              type="number"
              min={1}
              step={1}
              value={form.cycle_length}
              onChange={(e) => set("cycle_length", parseFloat(e.target.value) || 24)}
            />
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4 }}>
              Repetition period (e.g. 24 = one day)
            </p>
          </div>

          {/* Active toggle */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "12px 14px",
              borderRadius: "var(--radius-md)",
              background: "var(--surface-2)",
              cursor: "pointer",
            }}
            onClick={() => set("is_active", !form.is_active)}
          >
            <div
              style={{
                width: 40,
                height: 22,
                borderRadius: 11,
                background: form.is_active ? "#10b981" : "var(--border)",
                position: "relative",
                transition: "background 0.2s",
                flexShrink: 0,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 3,
                  left: form.is_active ? 21 : 3,
                  width: 16,
                  height: 16,
                  borderRadius: "50%",
                  background: "#fff",
                  transition: "left 0.2s",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                }}
              />
            </div>
            <span style={{ fontSize: "0.9375rem", fontWeight: 500 }}>
              {form.is_active ? "Active" : "Inactive"}
            </span>
          </div>

          {/* Error */}
          {err && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "10px 14px",
                borderRadius: "var(--radius-md)",
                background: "rgba(239, 68, 68, 0.08)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                color: "var(--error)",
                fontSize: "0.875rem",
              }}
            >
              <AlertTriangle size={14} />
              {err}
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button
              id="shift-modal-save"
              type="submit"
              className="btn btn-primary"
              disabled={saving}
              style={{ background: "linear-gradient(135deg, #10b981, #059669)", borderColor: "transparent", minWidth: 100 }}
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
              {saving ? "Saving…" : "Save Shift"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────
export default function ShiftsClient() {
  const [shifts, setShifts] = useState<MachineShift[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [filterMachine, setFilterMachine] = useState("");

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<MachineShift | null>(null);
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleting, setDeleting] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getShifts(!showAll);
      setShifts(data);
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Failed to load shifts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showAll]);

  const openAdd = () => {
    setEditing(null);
    setModalOpen(true);
  };

  const openEdit = (s: MachineShift) => {
    setEditing(s);
    setModalOpen(true);
  };

  const handleSave = async (form: MachineShiftIn) => {
    setSaving(true);
    try {
      if (editing) {
        await updateShift(editing.id, form);
      } else {
        await createShift(form);
      }
      setModalOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(id);
    try {
      await deleteShift(id);
      setShifts((prev) => prev.filter((s) => s.id !== id));
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Delete failed.");
    } finally {
      setDeleting(null);
    }
  };

  // Unique machines for filter
  const machines = Array.from(new Set(shifts.map((s) => s.machine_id))).sort();

  const filtered = filterMachine
    ? shifts.filter((s) => s.machine_id === filterMachine)
    : shifts;

  return (
    <>
      <div className="animate-fade-in" style={{ maxWidth: 1200 }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 16,
            marginBottom: 32,
            flexWrap: "wrap",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 12,
                  background: "linear-gradient(135deg, #10b981, #059669)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Clock size={20} color="#fff" />
              </div>
              <h1 style={{ fontSize: "1.75rem" }}>Shift Management</h1>
            </div>
            <p style={{ color: "var(--text-secondary)" }}>
              Configure working shift windows per machine for production scheduling.
            </p>
          </div>
          <button
            id="add-shift-btn"
            className="btn btn-primary"
            onClick={openAdd}
            style={{
              background: "linear-gradient(135deg, #10b981, #059669)",
              borderColor: "transparent",
              gap: 8,
            }}
          >
            <Plus size={16} />
            Add Shift
          </button>
        </div>

        {/* Toolbar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 20,
            flexWrap: "wrap",
          }}
        >
          {/* Machine filter */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Filter size={14} style={{ color: "var(--text-muted)" }} />
            <select
              id="shifts-machine-filter"
              className="input"
              style={{ height: 36, paddingTop: 0, paddingBottom: 0, minWidth: 160 }}
              value={filterMachine}
              onChange={(e) => setFilterMachine(e.target.value)}
            >
              <option value="">All Machines</option>
              {machines.map((m) => (
                <option key={m} value={m}>Machine {m}</option>
              ))}
            </select>
          </div>

          {/* Active toggle */}
          <button
            id="shifts-show-all"
            className={`btn ${showAll ? "btn-secondary" : "btn-ghost"}`}
            onClick={() => setShowAll((v) => !v)}
            style={{ height: 36, fontSize: "0.875rem" }}
          >
            {showAll ? "Show Active Only" : "Show All (inc. Inactive)"}
          </button>

          <span style={{ marginLeft: "auto", fontSize: "0.875rem", color: "var(--text-muted)" }}>
            {filtered.length} shift{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Error */}
        {error && (
          <div
            className="card"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginBottom: 20,
              borderColor: "rgba(239,68,68,0.2)",
              background: "rgba(239,68,68,0.04)",
              color: "var(--error)",
              fontSize: "0.9rem",
            }}
          >
            <AlertTriangle size={16} />
            {error}
            <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto" }} onClick={load}>
              Retry
            </button>
          </div>
        )}

        {/* Table / Loading / Empty */}
        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
            <Loader2 size={36} className="animate-spin" style={{ color: "#10b981" }} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="card" style={{ textAlign: "center", padding: "60px 24px" }}>
            <div
              style={{
                width: 72,
                height: 72,
                borderRadius: 20,
                background: "linear-gradient(135deg, rgba(16,185,129,0.12), rgba(5,150,105,0.08))",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px",
              }}
            >
              <Clock size={32} style={{ color: "#10b981" }} />
            </div>
            <h3 style={{ fontSize: "1.125rem", marginBottom: 8 }}>No shifts configured yet</h3>
            <p style={{ color: "var(--text-secondary)", marginBottom: 24, maxWidth: 380, margin: "0 auto 24px" }}>
              Add shift windows to define when machines are available during production.
            </p>
            <button
              id="empty-add-shift-btn"
              className="btn btn-primary"
              onClick={openAdd}
              style={{ background: "linear-gradient(135deg, #10b981, #059669)", borderColor: "transparent" }}
            >
              <Plus size={16} />
              Add Your First Shift
            </button>
          </div>
        ) : (
          <div className="card overflow-hidden p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-2)" }}>
                    <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Machine</th>
                    <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Shift</th>
                    <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Hours</th>
                    <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Cycle (min)</th>
                    <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Status</th>
                    <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Created</th>
                    <th style={{ padding: "12px 16px", textAlign: "right", fontWeight: 600, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s, i) => (
                    <tr
                      key={s.id}
                      style={{
                        borderBottom: "1px solid var(--border)",
                        background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-2)")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)")}
                    >
                      <td style={{ padding: "12px 16px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 6,
                            fontWeight: 600,
                            color: "var(--text-primary)",
                          }}
                        >
                          <span
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: "50%",
                              background: "#10b981",
                              display: "inline-block",
                              flexShrink: 0,
                            }}
                          />
                          Machine {s.machine_id}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <ShiftBadge name={s.shift_name} />
                      </td>
                      <td style={{ padding: "12px 16px", fontFamily: "monospace", color: "var(--text-primary)" }}>
                        {s.shift_start} – {s.shift_end} tu
                      </td>
                      <td style={{ padding: "12px 16px", color: "var(--text-secondary)" }}>
                        {s.cycle_length} min
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 5,
                            padding: "2px 10px",
                            borderRadius: 999,
                            fontSize: "0.8125rem",
                            fontWeight: 600,
                            background: s.is_active ? "rgba(16,185,129,0.1)" : "rgba(100,116,139,0.1)",
                            color: s.is_active ? "#10b981" : "var(--text-muted)",
                            border: `1px solid ${s.is_active ? "rgba(16,185,129,0.25)" : "rgba(100,116,139,0.2)"}`,
                          }}
                        >
                          <span
                            style={{
                              width: 6,
                              height: 6,
                              borderRadius: "50%",
                              background: s.is_active ? "#10b981" : "var(--text-muted)",
                            }}
                          />
                          {s.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: 6 }}>
                          <button
                            id={`edit-shift-${s.id}`}
                            className="btn btn-ghost btn-sm"
                            onClick={() => openEdit(s)}
                            title="Edit shift"
                            style={{ padding: "4px 8px" }}
                          >
                            <Pencil size={13} />
                          </button>
                          <button
                            id={`delete-shift-${s.id}`}
                            className="btn btn-ghost btn-sm"
                            onClick={() => handleDelete(s.id)}
                            disabled={deleting === s.id}
                            title="Delete shift"
                            style={{ padding: "4px 8px", color: "var(--error)" }}
                          >
                            {deleting === s.id ? (
                              <Loader2 size={13} className="animate-spin" />
                            ) : (
                              <Trash2 size={13} />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Stats cards */}
        {!loading && shifts.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: 16,
              marginTop: 24,
            }}
          >
            {[
              { label: "Total Shifts", value: shifts.length },
              { label: "Active", value: shifts.filter((s) => s.is_active).length, color: "#10b981" },
              { label: "Inactive", value: shifts.filter((s) => !s.is_active).length, color: "var(--text-muted)" },
              { label: "Machines", value: machines.length },
            ].map(({ label, value, color }) => (
              <div key={label} className="card" style={{ padding: "16px 20px" }}>
                <div style={{ fontSize: "1.75rem", fontWeight: 700, color: color ?? "var(--text-primary)", lineHeight: 1.1 }}>
                  {value}
                </div>
                <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
      <ShiftModal
        isOpen={modalOpen}
        title={editing ? "Edit Shift" : "Add New Shift"}
        onClose={() => setModalOpen(false)}
        onSubmit={handleSave}
        initial={
          editing
            ? {
                machine_id: editing.machine_id,
                shift_name: editing.shift_name,
                shift_start: editing.shift_start,
                shift_end: editing.shift_end,
                cycle_length: editing.cycle_length,
                is_active: editing.is_active,
              }
            : undefined
        }
        saving={saving}
      />
    </>
  );
}
