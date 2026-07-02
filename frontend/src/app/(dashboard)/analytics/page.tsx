"use client";

import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import {
  BarChart3,
  TrendingUp,
  Cpu,
  Clock,
  CheckCircle,
  Grid,
} from "lucide-react";
import {
  getAnalyticsSummary,
  getAnalyticsTrends,
  getUtilizationHeatmap,
  getAlgorithmComparison,
  getTardinessDistribution,
  AnalyticsSummaryData,
  TrendsResponse,
  HeatmapResponse,
  AlgorithmComparisonResponse,
  TardinessDistributionResponse,
} from "@/lib/api";

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummaryData | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [heatmap, setHeatmap] = useState<HeatmapResponse | null>(null);
  const [comparison, setComparison] = useState<AlgorithmComparisonResponse | null>(null);
  const [tardiness, setTardiness] = useState<TardinessDistributionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const [sum, trend, heat, comp, tard] = await Promise.all([
        getAnalyticsSummary(),
        getAnalyticsTrends(20),
        getUtilizationHeatmap(10),
        getAlgorithmComparison(),
        getTardinessDistribution(10, 5),
      ]);
      setSummary(sum);
      setTrends(trend);
      setHeatmap(heat);
      setComparison(comp);
      setTardiness(tard);
    } catch (err: any) {
      console.error(err);
      setError(err?.message || "Failed to fetch analytics data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-indigo-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto mt-8 p-6 rounded-2xl bg-red-950/30 border border-red-500/20 text-center">
        <h3 className="text-red-400 font-bold text-lg mb-2">Error Loading Analytics</h3>
        <p className="text-slate-400 text-sm mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl px-5 py-2.5 transition-all"
        >
          Try Again
        </button>
      </div>
    );
  }

  const noData = !summary || summary.total_runs === 0;

  if (noData) {
    return (
      <div className="max-w-4xl mx-auto mt-8 text-center p-12 rounded-2xl border border-dashed border-white/10 bg-[#0f1115]/50">
        <BarChart3 size={64} className="text-slate-500 opacity-40 mx-auto mb-4" />
        <h3 className="text-white font-bold text-xl mb-2">No Analytics Data Yet</h3>
        <p className="text-slate-400 text-sm max-w-md mx-auto mb-6">
          Optimize your first production schedule using the generator. Run schedules will automatically populate your dashboard charts and metrics.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-[1440px] mx-auto px-4 py-6 font-sans">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Analytics Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">
          Monitor scheduler runs, makespan improvements, and machine utility history.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Optimizations</p>
              <h3 className="text-3xl font-extrabold text-white mt-2">{summary.total_runs}</h3>
            </div>
            <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400">
              <Cpu size={20} />
            </div>
          </div>
        </div>

        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Makespan</p>
              <h3 className="text-3xl font-extrabold text-white mt-2">
                {summary.avg_makespan} <span className="text-xs text-slate-400 font-normal">units</span>
              </h3>
            </div>
            <div className="p-3 bg-blue-500/10 rounded-xl text-blue-400">
              <Clock size={20} />
            </div>
          </div>
        </div>

        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg Machine Utilization</p>
              <h3 className="text-3xl font-extrabold text-white mt-2">
                {(summary.avg_utilization * 100).toFixed(1)}%
              </h3>
            </div>
            <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
              <TrendingUp size={20} />
            </div>
          </div>
        </div>

        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-lg">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg On-Time Rate</p>
              <h3 className="text-3xl font-extrabold text-white mt-2">
                {summary.avg_on_time_percent.toFixed(1)}%
              </h3>
            </div>
            <div className="p-3 bg-purple-500/10 rounded-xl text-purple-400">
              <CheckCircle size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Makespan & Tardiness Trends Line Chart */}
        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-md">
          <h3 className="text-white font-bold text-lg mb-6">Optimization Performance Trends</h3>
          <div className="h-[300px]">
            {trends && trends.points.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends.points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3b" />
                  <XAxis dataKey="task_id" tickFormatter={(v) => v.slice(0, 4)} stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#1c1e24", border: "1px solid rgba(255,255,255,0.08)" }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                  <Line type="monotone" dataKey="makespan" stroke="#4f46e5" strokeWidth={2.5} name="Makespan" activeDot={{ r: 8 }} />
                  <Line type="monotone" dataKey="total_tardiness" stroke="#ef4444" strokeWidth={2.5} name="Tardiness" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-sm">No trends data.</div>
            )}
          </div>
        </div>

        {/* Algorithm Comparison Bar Chart */}
        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-md">
          <h3 className="text-white font-bold text-lg mb-6">Algorithm Average Makespan (Lower is Better)</h3>
          <div className="h-[300px]">
            {comparison && comparison.algorithms.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparison.algorithms}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3b" />
                  <XAxis dataKey="algorithm" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#1c1e24", border: "1px solid rgba(255,255,255,0.08)" }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                  <Bar dataKey="avg_makespan" fill="#6366f1" radius={[4, 4, 0, 0]} name="Avg Makespan" />
                  <Bar dataKey="best_makespan" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Best Makespan" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-sm">No algorithm comparison data.</div>
            )}
          </div>
        </div>
      </div>

      {/* Heatmap & Histogram Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Machine Utilization Heatmap */}
        <div className="lg:col-span-2 bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-md">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-white font-bold text-lg">Machine Utilization Heatmap</h3>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-900 rounded-sm" /> &lt; 50%</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-600 rounded-sm" /> 50% - 75%</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-400 rounded-sm" /> &gt; 75%</div>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            {heatmap && heatmap.machines.length > 0 ? (
              <div className="min-w-[500px]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr>
                      <th className="p-2.5 font-semibold text-slate-400">Machine</th>
                      {heatmap.runs.map((r, i) => (
                        <th key={r} className="p-2.5 text-center font-semibold text-slate-400">
                          Run {i + 1}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heatmap.machines.map((mId) => (
                      <tr key={mId} className="border-t border-white/5">
                        <td className="p-2.5 font-semibold text-white">Machine {mId}</td>
                        {heatmap.runs.map((rId) => {
                          const cell = heatmap.cells.find((c) => c.machine_id === mId && c.task_id === rId);
                          const val = cell ? cell.utilization : 0;
                          
                          // Determine color based on utilization
                          let bgClass = "bg-indigo-950/40 text-indigo-400/50";
                          if (val >= 0.75) bgClass = "bg-indigo-500 text-white font-semibold";
                          else if (val >= 0.5) bgClass = "bg-indigo-700 text-white/90";
                          else if (val > 0) bgClass = "bg-indigo-900/60 text-indigo-300";
                          
                          return (
                            <td key={rId} className="p-1">
                              <div className={`p-2 rounded-lg text-center transition-all ${bgClass}`}>
                                {(val * 100).toFixed(0)}%
                              </div>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[200px] text-slate-500 text-sm">No utilization data.</div>
            )}
          </div>
        </div>

        {/* Tardiness Distribution Histogram */}
        <div className="bg-[#15171e] border border-white/5 rounded-2xl p-6 shadow-md">
          <h3 className="text-white font-bold text-lg mb-6">Tardiness Distribution</h3>
          <div className="h-[250px]">
            {tardiness && tardiness.buckets.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={tardiness.buckets.map((b, idx) => ({
                    bucket: b,
                    jobs: tardiness.counts[idx],
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2e3b" />
                  <XAxis dataKey="bucket" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={{ backgroundColor: "#1c1e24", border: "1px solid rgba(255,255,255,0.08)" }} />
                  <Bar dataKey="jobs" fill="#a855f7" radius={[4, 4, 0, 0]} name="Job Count" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-500 text-sm">No tardiness data.</div>
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-white/5 text-center text-xs text-slate-400">
            Analyzing {tardiness?.total_jobs || 0} jobs across recent run history.
          </div>
        </div>

      </div>

    </div>
  );
}
