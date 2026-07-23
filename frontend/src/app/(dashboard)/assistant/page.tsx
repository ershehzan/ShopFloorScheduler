import type { Metadata } from "next";
import AssistantClient from "./AssistantClient";

export const metadata: Metadata = {
  title: "AI Assistant — ShopFloorScheduler",
  description: "Chat with your scheduling assistant to query runs, machine health, and more.",
};

export default function AssistantPage() {
  return <AssistantClient />;
}
