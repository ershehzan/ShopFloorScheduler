import type { Metadata } from "next";
import { FileText, Download } from "lucide-react";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Reports — ShopFloorScheduler",
  description: "Download PDF, Excel, and CSV reports for your schedule runs.",
};

export default function ReportsPage() {
  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: 4 }}>Reports</h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Download schedule reports in PDF, Excel, and CSV formats.
        </p>
      </div>
      <div className="card" style={{ textAlign: "center", padding: 60 }}>
        <FileText size={48} style={{ color: "var(--text-muted)", opacity: 0.4, marginBottom: 16 }} />
        <h3 style={{ fontSize: "1.125rem", marginBottom: 8 }}>No reports yet</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem", marginBottom: 20 }}>
          Complete a schedule run to generate downloadable reports.
        </p>
        <Link href="/schedule/new" className="btn btn-primary" id="reports-new-schedule-btn">
          <Download size={16} />
          Create Your First Schedule
        </Link>
      </div>
    </div>
  );
}
