import type { Metadata } from "next";
import DashboardClient from "./DashboardClient";

export const metadata: Metadata = {
  title: "Dashboard — ShopFloorScheduler",
  description: "Overview of your shop floor scheduling operations, KPIs, and recent runs.",
};

export default function DashboardPage() {
  return <DashboardClient />;
}
