"use client";

import React, { useState } from "react";
import Sidebar from "./Sidebar";
import TopNav from "./TopNav";

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="dashboard-layout">
      <TopNav sidebarCollapsed={collapsed} />
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <main
        className={`main-content ${collapsed ? "sidebar-collapsed" : ""}`}
        style={{ padding: "32px", minHeight: "100vh" }}
      >
        {children}
      </main>
    </div>
  );
}
