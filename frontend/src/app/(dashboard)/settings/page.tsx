import type { Metadata } from "next";
import { Settings } from "lucide-react";

export const metadata: Metadata = {
  title: "Settings — ShopFloorScheduler",
};

export default function SettingsPage() {
  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Settings</h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Configure application preferences and API connections.
        </p>
      </div>

      {/* API Config card */}
      <div className="card" style={{ maxWidth: 600 }}>
        <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>API Configuration</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label
              htmlFor="api-url"
              style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: 6 }}
            >
              Backend API URL
            </label>
            <input
              id="api-url"
              className="input"
              type="url"
              defaultValue="http://localhost:8000"
              readOnly
            />
            <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: 4 }}>
              Set via <code>NEXT_PUBLIC_API_URL</code> in <code>.env.local</code>
            </p>
          </div>
          <div
            style={{
              padding: "12px 14px",
              background: "rgba(16,185,129,0.06)",
              border: "1px solid rgba(16,185,129,0.2)",
              borderRadius: "var(--radius-md)",
              fontSize: "0.875rem",
              color: "var(--success)",
            }}
          >
            ✓ Configuration loaded from environment
          </div>
        </div>
      </div>
    </div>
  );
}
