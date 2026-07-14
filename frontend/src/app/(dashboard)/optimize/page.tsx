import type { Metadata } from "next";
import OptimizeWorkspace from "./OptimizeWorkspace";

export const metadata: Metadata = {
  title: "Optimization — ShopFloorScheduler",
  description: "Multi-objective schedule optimization and algorithm comparison.",
};

export default function OptimizePage() {
  return <OptimizeWorkspace />;
}

