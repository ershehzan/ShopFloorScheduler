"use client";

import React, { useState, useEffect } from "react";
import { Bell, Moon, Sun, Search, User } from "lucide-react";

interface TopNavProps {
  sidebarCollapsed: boolean;
}

export default function TopNav({ sidebarCollapsed }: TopNavProps) {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [dark]);

  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: "var(--topnav-height)",
        background: "var(--surface)",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        padding: "0 24px",
        gap: 16,
        zIndex: 50,
        backdropFilter: "blur(8px)",
      }}
    >
      {/* Offset for sidebar */}
      <div
        style={{
          width: sidebarCollapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-width)",
          transition: "width var(--transition-base)",
          flexShrink: 0,
        }}
      />

      {/* Search */}
      <div
        style={{
          flex: 1,
          maxWidth: 400,
          position: "relative",
        }}
      >
        <Search
          size={16}
          style={{
            position: "absolute",
            left: 12,
            top: "50%",
            transform: "translateY(-50%)",
            color: "var(--text-muted)",
          }}
        />
        <input
          className="input"
          type="text"
          placeholder="Search schedules, jobs, machines..."
          style={{ paddingLeft: 36, height: 36 }}
        />
      </div>

      <div style={{ flex: 1 }} />

      {/* Actions */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {/* Dark mode toggle */}
        <button
          onClick={() => setDark(!dark)}
          className="btn btn-ghost"
          style={{ width: 36, height: 36, padding: 0, borderRadius: "var(--radius-md)" }}
          title={dark ? "Switch to light mode" : "Switch to dark mode"}
          id="dark-mode-toggle"
        >
          {dark ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Notifications */}
        <button
          className="btn btn-ghost"
          style={{ width: 36, height: 36, padding: 0, borderRadius: "var(--radius-md)", position: "relative" }}
          title="Notifications"
          id="notifications-btn"
        >
          <Bell size={16} />
          <span
            style={{
              position: "absolute",
              top: 6,
              right: 6,
              width: 8,
              height: 8,
              background: "var(--error)",
              borderRadius: "50%",
              border: "2px solid var(--surface)",
            }}
          />
        </button>

        {/* User avatar */}
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg, var(--secondary), var(--accent))",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            flexShrink: 0,
          }}
          title="User profile"
        >
          <User size={16} color="#fff" />
        </div>
      </div>
    </header>
  );
}
