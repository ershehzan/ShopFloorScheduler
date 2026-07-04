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
  Loader2,
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
    await Promise.resolve();
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
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to fetch analytics data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData();
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[500px]">
        <Loader2 className="animate-spin text-accent h-12 w-12" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto mt-8 p-6 card text-center" style={{ borderColor: "var(--error)" }}>
        <h3 className="text-red-600 dark:text-red-400 font-bold text-lg mb-2">Error Loading Analytics</h3>
        <p className="text-secondary-text text-sm mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="btn btn-primary"
        >
          Try Again
        </button>
      </div>
    );
  }

  const noData = !summary || summary.total_runs === 0;

  if (noData) {
    return (
      <div className="max-w-4xl mx-auto mt-8 text-center p-12 card border-dashed">
        <BarChart3 size={64} className="text-muted opacity-40 mx-auto mb-4" />
        <h3 className="text-primary-text font-bold text-xl mb-2">No Analytics Data Yet</h3>
        <p className="text-secondary-text text-sm max-w-md mx-auto mb-6">
          Optimize your first production schedule using the generator. Run schedules will automatically populate your dashboard charts and metrics.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-[1440px] mx-auto px-4 py-6 font-sans">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-extrabold text-primary-text tracking-tight">Analytics Dashboard</h1>
        <p className="text-secondary-text text-sm mt-1">
          Monitor scheduler runs, makespan improvements, and machine utility history.
        </p>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card kpi-card-blue flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-secondary-text uppercase tracking-wider">Total Optimizations</p>
              <h3 className="text-3xl font-extrabold text-primary-text mt-2">{summary.total_runs}</h3>
            </div>
            <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-600 dark:text-indigo-400">
              <Cpu size={20} />
            </div>
          </div>
        </div>

        <div className="card kpi-card-cyan flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-secondary-text uppercase tracking-wider">Avg Makespan</p>
              <h3 className="text-3xl font-extrabold text-primary-text mt-2">
                {summary.avg_makespan.toFixed(1)} <span className="text-xs text-secondary-text font-normal">units</span>
              </h3>
            </div>
            <div className="p-3 bg-blue-500/10 rounded-xl text-blue-600 dark:text-blue-400">
              <Clock size={20} />
            </div>
          </div>
        </div>

        <div className="card kpi-card-green flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-secondary-text uppercase tracking-wider">Avg Machine Utilization</p>
              <h3 className="text-3xl font-extrabold text-primary-text mt-2">
                {(summary.avg_utilization * 100).toFixed(1)}%
              </h3>
            </div>
            <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-600 dark:text-emerald-400">
              <TrendingUp size={20} />
            </div>
          </div>
        </div>

        <div className="card kpi-card-amber flex flex-col justify-between" style={{ padding: 20 }}>
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-secondary-text uppercase tracking-wider">Avg On-Time Rate</p>
              <h3 className="text-3xl font-extrabold text-primary-text mt-2">
                {summary.avg_on_time_percent.toFixed(1)}%
              </h3>
            </div>
            <div className="p-3 bg-purple-500/10 rounded-xl text-purple-600 dark:text-purple-400">
              <CheckCircle size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* Main Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Makespan & Tardiness Trends Line Chart */}
        <div className="card">
          <h3 className="text-primary-text font-bold text-lg mb-6">Optimization Performance Trends</h3>
          <div className="h-[300px]">
            {trends && trends.points.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trends.points}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="task_id" tickFormatter={(v) => v.slice(0, 4)} stroke="var(--text-muted)" fontSize={11} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }} labelStyle={{ color: "var(--text-primary)" }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                  <Line type="monotone" dataKey="makespan" stroke="var(--secondary)" strokeWidth={2.5} name="Makespan" activeDot={{ r: 8 }} />
                  <Line type="monotone" dataKey="total_tardiness" stroke="var(--error)" strokeWidth={2.5} name="Tardiness" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-secondary-text text-sm">No trends data.</div>
            )}
          </div>
        </div>

        {/* Algorithm Comparison Bar Chart */}
        <div className="card">
          <h3 className="text-primary-text font-bold text-lg mb-6">Algorithm Average Makespan (Lower is Better)</h3>
          <div className="h-[300px]">
            {comparison && comparison.algorithms.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={comparison.algorithms}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="algorithm" stroke="var(--text-muted)" fontSize={11} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }} labelStyle={{ color: "var(--text-primary)" }} />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                  <Bar dataKey="avg_makespan" fill="var(--secondary)" radius={[4, 4, 0, 0]} name="Avg Makespan" />
                  <Bar dataKey="best_makespan" fill="var(--accent)" radius={[4, 4, 0, 0]} name="Best Makespan" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-secondary-text text-sm">No algorithm comparison data.</div>
            )}
          </div>
        </div>
      </div>

      {/* Heatmap & Histogram Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Machine Utilization Heatmap */}
        <div className="lg:col-span-2 card">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <h3 className="text-primary-text font-bold text-lg">Machine Utilization Heatmap</h3>
            <div className="flex items-center gap-4 text-xs text-secondary-text">
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-200 dark:bg-indigo-900/60 rounded-sm" /> &lt; 50%</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-400 dark:bg-indigo-700 rounded-sm" /> 50% - 75%</div>
              <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-indigo-600 dark:bg-indigo-500 rounded-sm" /> &gt; 75%</div>
            </div>
          </div>
          
          <div className="overflow-x-auto">
            {heatmap && heatmap.machines.length > 0 ? (
              <div className="min-w-[500px]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-surface-2/50">
                      <th className="p-2.5 font-semibold text-secondary-text border-b border-border">Machine</th>
                      {heatmap.runs.map((r, i) => (
                        <th key={r} className="p-2.5 text-center font-semibold text-secondary-text border-b border-border">
                          Run {i + 1}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {heatmap.machines.map((mId) => (
                      <tr key={mId} className="border-b border-border hover:bg-surface-2/20">
                        <td className="p-2.5 font-semibold text-primary-text">Machine {mId}</td>
                        {heatmap.runs.map((rId) => {
                          const cell = heatmap.cells.find((c) => c.machine_id === mId && c.task_id === rId);
                          const val = cell ? cell.utilization : 0;
                          
                          // Determine color based on utilization
                          let bgClass = "bg-slate-100 dark:bg-slate-900/40 text-slate-500 dark:text-slate-400/50";
                          if (val >= 0.75) bgClass = "bg-indigo-600 dark:bg-indigo-500 text-white font-semibold shadow-sm";
                          else if (val >= 0.5) bgClass = "bg-indigo-400 dark:bg-indigo-700 text-white dark:text-white/90 shadow-sm";
                          else if (val > 0) bgClass = "bg-indigo-200 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300";
                          
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
              <div className="flex items-center justify-center h-[200px] text-secondary-text text-sm">No utilization data.</div>
            )}
          </div>
        </div>

        {/* Tardiness Distribution Histogram */}
        <div className="card">
          <h3 className="text-primary-text font-bold text-lg mb-6">Tardiness Distribution</h3>
          <div className="h-[250px]">
            {tardiness && tardiness.buckets.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={tardiness.buckets.map((b, idx) => ({
                    bucket: b,
                    jobs: tardiness.counts[idx],
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="bucket" stroke="var(--text-muted)" fontSize={11} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={{ backgroundColor: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-primary)" }} labelStyle={{ color: "var(--text-primary)" }} />
                  <Bar dataKey="jobs" fill="#a855f7" radius={[4, 4, 0, 0]} name="Job Count" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-secondary-text text-sm">No tardiness data.</div>
            )}
          </div>
          <div className="mt-4 pt-4 border-t border-border text-center text-xs text-secondary-text">
            Analyzing {tardiness?.total_jobs || 0} jobs across recent run history.
          </div>
        </div>

      </div>

    </div>
  );
}

