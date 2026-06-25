"use client";

import React from "react";
import { Download, FileText, Table } from "lucide-react";
import { resourceUrl } from "@/lib/api";

interface ExportButtonsProps {
  taskId: string;
  excelUrl: string | null;
  chartUrl: string | null;
}

export default function ExportButtons({ taskId, excelUrl, chartUrl }: ExportButtonsProps) {
  const resolvedExcel = resourceUrl(excelUrl);
  const resolvedChart = resourceUrl(chartUrl);

  const buttons = [
    {
      id: "export-excel-btn",
      label: "Excel Report",
      href: resolvedExcel,
      icon: Table,
      desc: "Full schedule data (.xlsx)",
      color: "var(--success)",
    },
    {
      id: "export-gantt-btn",
      label: "Gantt Chart",
      href: resolvedChart,
      icon: FileText,
      desc: "PNG schedule visualization",
      color: "var(--secondary)",
    },
  ];

  return (
    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
      {buttons.map(({ id, label, href, icon: Icon, desc, color }) =>
        href ? (
          <a
            key={id}
            id={id}
            href={href}
            download
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ gap: 8, height: 40, fontSize: "0.875rem" }}
          >
            <Download size={14} />
            {label}
          </a>
        ) : (
          <button
            key={id}
            id={id}
            disabled
            className="btn btn-secondary"
            style={{ gap: 8, height: 40, fontSize: "0.875rem", opacity: 0.4 }}
          >
            <Download size={14} />
            {label}
          </button>
        )
      )}
    </div>
  );
}
