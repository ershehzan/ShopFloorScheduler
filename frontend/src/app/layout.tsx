import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShopFloorScheduler — AI-Powered Production Scheduling",
  description:
    "Optimize shop floor schedules using genetic algorithms and intelligent scheduling. Minimize makespan, reduce tardiness, and maximize machine utilization.",
  keywords: [
    "shop floor scheduling",
    "production optimization",
    "genetic algorithm",
    "manufacturing scheduler",
    "Gantt chart",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
