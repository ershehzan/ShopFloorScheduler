"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface ComparisonChartProps {
  data: {
    algorithm: string;
    makespan: number;
    total_tardiness: number;
    avg_flow_time: number;
    on_time_percent: number;
  }[];
}

export default function ComparisonChart({ data }: ComparisonChartProps) {
  return (
    <div style={{ width: "100%", height: 350 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.08)" />
          <XAxis 
            dataKey="algorithm" 
            stroke="var(--text-muted)" 
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
          />
          <YAxis 
            yAxisId="left"
            orientation="left"
            stroke="var(--secondary)" 
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
            label={{ value: "Makespan (Time Units)", angle: -90, position: "insideLeft", fill: "var(--secondary)", style: { fontSize: 12, textAnchor: "middle" } }}
          />
          <YAxis 
            yAxisId="right"
            orientation="right"
            stroke="var(--accent)" 
            tick={{ fill: "var(--text-secondary)", fontSize: 12 }}
            label={{ value: "Total Tardiness", angle: 90, position: "insideRight", fill: "var(--accent)", style: { fontSize: 12, textAnchor: "middle" } }}
          />
          <Tooltip
            contentStyle={{
              background: "rgba(17, 24, 39, 0.95)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "8px",
              boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
              color: "#fff",
            }}
            itemStyle={{ color: "#fff" }}
          />
          <Legend 
            wrapperStyle={{ paddingTop: 10, fontSize: 12 }}
          />
          <Bar yAxisId="left" dataKey="makespan" name="Makespan (left axis)" fill="var(--secondary)" radius={[4, 4, 0, 0]} maxBarSize={40} />
          <Bar yAxisId="right" dataKey="total_tardiness" name="Total Tardiness (right axis)" fill="var(--accent)" radius={[4, 4, 0, 0]} maxBarSize={40} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
