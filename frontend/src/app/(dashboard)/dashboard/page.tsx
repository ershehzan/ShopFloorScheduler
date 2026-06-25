import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Activity, Clock, Cpu, TrendingUp, Plus, ChevronRight } from "lucide-react";

export const metadata: Metadata = {
  title: "Dashboard — ShopFloorScheduler",
  description: "Overview of your shop floor scheduling operations, KPIs, and recent runs.",
};

const KPI_CARDS = [
  {
    label: "Avg Makespan",
    value: "—",
    unit: "time units",
    change: null,
    icon: Clock,
    accent: "kpi-card-blue",
  },
  {
    label: "Machine Utilization",
    value: "—",
    unit: "%",
    change: null,
    icon: Cpu,
    accent: "kpi-card-cyan",
  },
  {
    label: "On-Time Delivery",
    value: "—",
    unit: "%",
    change: null,
    icon: TrendingUp,
    accent: "kpi-card-green",
  },
  {
    label: "Total Runs",
    value: "0",
    unit: "schedules",
    change: null,
    icon: Activity,
    accent: "kpi-card-amber",
  },
];

export default function DashboardPage() {
  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 32,
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div>
          <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Dashboard</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
            Monitor your production scheduling operations and performance metrics.
          </p>
        </div>
        <Link
          href="/schedule/new"
          className="btn btn-primary"
          id="new-schedule-btn"
          style={{ gap: 8 }}
        >
          <Plus size={16} />
          New Schedule
        </Link>
      </div>

      {/* KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 20,
          marginBottom: 32,
        }}
      >
        {KPI_CARDS.map(({ label, value, unit, icon: Icon, accent }) => (
          <div key={label} className={`card ${accent}`} style={{ padding: 20 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 16,
              }}
            >
              <span style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                {label}
              </span>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg-secondary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon size={16} style={{ color: "var(--text-secondary)" }} />
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
            <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{unit}</div>
          </div>
        ))}
      </div>

      {/* Two-column: Quick Actions + Welcome */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          marginBottom: 32,
        }}
      >
        {/* Quick Actions */}
        <div className="card">
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Quick Actions</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { href: "/schedule/new", label: "Upload Job Data & Schedule", desc: "Start a new optimization run", color: "var(--secondary)" },
              { href: "/reports", label: "Download Reports", desc: "PDF, Excel, and CSV exports", color: "var(--accent)" },
              { href: "/analytics", label: "View Analytics", desc: "Trend charts and utilization", color: "var(--success)" },
            ].map(({ href, label, desc, color }) => (
              <Link
                key={href}
                href={href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 16px",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border)",
                  textDecoration: "none",
                  color: "var(--text-primary)",
                  transition: "all var(--transition-fast)",
                  gap: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: color,
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{label}</div>
                    <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{desc}</div>
                  </div>
                </div>
                <ChevronRight size={16} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
              </Link>
            ))}
          </div>
        </div>

        {/* Getting Started */}
        <div
          className="card"
          style={{
            background: "linear-gradient(135deg, rgba(30,64,175,0.06), rgba(6,182,212,0.06))",
            borderColor: "rgba(37,99,235,0.2)",
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 8 }}>
            Getting Started
          </h3>
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: 20, lineHeight: 1.6 }}>
            Upload your Excel job data, configure the optimization algorithm, and generate
            a Gantt chart schedule in seconds.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {[
              "1. Prepare an Excel file with Jobs, Operations, and Machines sheets",
              "2. Click \"New Schedule\" and upload your file",
              "3. Choose algorithm (GA, FCFS, SPT, EDD, or WSPT)",
              "4. View the Gantt chart and download your report",
            ].map((step) => (
              <div
                key={step}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                }}
              >
                <span style={{ color: "var(--secondary)", fontWeight: 600, flexShrink: 0 }}>→</span>
                {step}
              </div>
            ))}
          </div>
          <Link
            href="/schedule/new"
            className="btn btn-primary"
            style={{ marginTop: 20, width: "100%" }}
            id="dashboard-get-started-btn"
          >
            Start Scheduling
            <ArrowRight size={16} />
          </Link>
        </div>
      </div>

      {/* Recent Runs placeholder */}
      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Recent Schedule Runs</h3>
          <Link
            href="/reports"
            style={{ fontSize: "0.8125rem", color: "var(--secondary)", textDecoration: "none", fontWeight: 500 }}
          >
            View all
          </Link>
        </div>
        <div
          style={{
            textAlign: "center",
            padding: "48px 24px",
            color: "var(--text-muted)",
          }}
        >
          <Activity size={40} style={{ marginBottom: 12, opacity: 0.4 }} />
          <p style={{ fontWeight: 500, marginBottom: 4 }}>No schedule runs yet</p>
          <p style={{ fontSize: "0.875rem" }}>
            Create your first schedule to see results here.
          </p>
          <Link
            href="/schedule/new"
            className="btn btn-primary"
            style={{ marginTop: 16, display: "inline-flex" }}
          >
            <Plus size={16} />
            Create Schedule
          </Link>
        </div>
      </div>
    </div>
  );
}
