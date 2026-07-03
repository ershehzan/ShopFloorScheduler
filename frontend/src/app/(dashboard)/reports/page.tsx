import type { Metadata } from "next";
import ReportsClient from "./ReportsClient";

export const metadata: Metadata = {
  title: "Reports — ShopFloorScheduler",
  description: "Download PDF, Excel, and CSV reports for your schedule runs.",
};

export default function ReportsPage() {
  return <ReportsClient />;
}
