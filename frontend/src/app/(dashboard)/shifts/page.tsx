import type { Metadata } from "next";
import ShiftsClient from "./ShiftsClient";

export const metadata: Metadata = {
  title: "Shift Management — ShopFloorScheduler",
  description: "Configure and manage machine shift windows for production scheduling.",
};

export default function ShiftsPage() {
  return <ShiftsClient />;
}
