"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CalendarClock,
  Zap,
  BarChart3,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Factory,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/schedule/new", label: "New Schedule", icon: CalendarClock },
  { href: "/optimize", label: "Optimization", icon: Zap },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: collapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-width)",
        position: "fixed",
        top: "var(--topnav-height)",
        left: 0,
        bottom: 0,
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        transition: "width var(--transition-base)",
        overflow: "hidden",
        zIndex: 40,
      }}
    >
      {/* Brand Logo */}
      {!collapsed && (
        <div
          style={{
            padding: "20px 24px 16px",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, var(--primary), var(--accent))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <Factory size={18} color="#fff" />
          </div>
          <div>
            <div
              style={{
                fontSize: "0.875rem",
                fontWeight: 700,
                color: "var(--text-primary)",
                lineHeight: 1.1,
              }}
            >
              ShopFloor
            </div>
            <div
              style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 500 }}
            >
              Scheduler
            </div>
          </div>
        </div>
      )}

      {collapsed && (
        <div
          style={{
            padding: "20px 0 16px",
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "linear-gradient(135deg, var(--primary), var(--accent))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Factory size={20} color="#fff" />
          </div>
        </div>
      )}

      <div style={{ height: 1, background: "var(--border)", margin: "0 16px" }} />

      {/* Navigation */}
      <nav style={{ flex: 1, padding: "8px 12px", overflowY: "auto" }}>
        <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.08em", padding: "12px 12px 6px", textTransform: "uppercase", display: collapsed ? "none" : "block" }}>
          Main Menu
        </div>
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: collapsed ? "10px 0" : "10px 12px",
                justifyContent: collapsed ? "center" : "flex-start",
                borderRadius: "var(--radius-md)",
                margin: "2px 0",
                textDecoration: "none",
                color: active ? "var(--secondary)" : "var(--text-secondary)",
                background: active ? "rgba(37, 99, 235, 0.08)" : "transparent",
                fontWeight: active ? 600 : 400,
                fontSize: "0.9375rem",
                transition: "all var(--transition-fast)",
                position: "relative",
              }}
            >
              {active && (
                <span
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "20%",
                    bottom: "20%",
                    width: 3,
                    borderRadius: "0 99px 99px 0",
                    background: "var(--secondary)",
                  }}
                />
              )}
              <Icon size={18} />
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Toggle button */}
      <div style={{ padding: "12px", borderTop: "1px solid var(--border)" }}>
        <button
          onClick={onToggle}
          className="btn btn-ghost"
          style={{
            width: "100%",
            height: 36,
            justifyContent: collapsed ? "center" : "flex-start",
            fontSize: "0.8125rem",
            color: "var(--text-muted)",
            gap: 8,
          }}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={16} /> : <><ChevronLeft size={16} /><span>Collapse</span></>}
        </button>
      </div>
    </aside>
  );
}
