import type { Metadata } from "next";
import { BarChart3, TrendingUp, Cpu } from "lucide-react";

export const metadata: Metadata = {
  title: "Analytics — ShopFloorScheduler",
  description: "Performance analytics and trend analysis for your scheduling operations.",
};

export default function AnalyticsPage() {
  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Analytics</h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Performance trends, utilization analysis, and scheduling insights.
        </p>
      </div>
      <div className="card" style={{ textAlign: "center", padding: 60 }}>
        <BarChart3 size={48} style={{ color: "var(--text-muted)", opacity: 0.4, marginBottom: 16 }} />
        <h3 style={{ fontSize: "1.125rem", marginBottom: 8 }}>Coming in Phase 5</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
          Run your first schedules to generate analytics data. Charts will appear here automatically.
        </p>
      </div>
    </div>
  );
}
