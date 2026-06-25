import type { Metadata } from "next";
import { Zap } from "lucide-react";

export const metadata: Metadata = {
  title: "Optimization — ShopFloorScheduler",
  description: "Multi-objective schedule optimization and algorithm comparison.",
};

export default function OptimizePage() {
  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Optimization</h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Compare algorithms, run what-if scenarios, and analyze trade-offs.
        </p>
      </div>
      <div className="card" style={{ textAlign: "center", padding: 60 }}>
        <Zap size={48} style={{ color: "var(--text-muted)", opacity: 0.4, marginBottom: 16 }} />
        <h3 style={{ fontSize: "1.125rem", marginBottom: 8 }}>Coming in Phase 5</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
          Algorithm comparison views and scenario simulation will be available here.
        </p>
      </div>
    </div>
  );
}
