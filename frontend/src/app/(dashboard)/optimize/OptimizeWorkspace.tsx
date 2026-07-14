"use client";

import React, { useState, useEffect, useRef } from "react";
import { 
  Zap, 
  Upload, 
  FileSpreadsheet, 
  Check, 
  Loader2, 
  BarChart3, 
  Calendar,
  Download,
  AlertTriangle,
  RefreshCw,
  Info
} from "lucide-react";
import { 
  runComparison, 
  getCompareStatus, 
  ComparisonRunResult, 
  resourceUrl,
  getAccessToken
} from "@/lib/api";
import ComparisonChart from "@/components/analytics/ComparisonChart";
import GanttChart from "@/components/gantt/GanttChart";

export default function OptimizeWorkspace() {
  // Input fields
  const [file, setFile] = useState<File | null>(null);
  const [setupTime, setSetupTime] = useState(2);
  const [algos, setAlgos] = useState({
    FCFS: true,
    SPT: true,
    EDD: true,
    WSPT: true,
    GA: true
  });
  
  // GA Params
  const [showGAParams, setShowGAParams] = useState(true);
  const [popSize, setPopSize] = useState(30);
  const [generations, setGenerations] = useState(50);
  const [mutationRate, setMutationRate] = useState(0.1);
  const [wMakespan, setWMakespan] = useState(0.6);
  const [wTardiness, setWTardiness] = useState(0.4);

  // Task Status
  const [status, setStatus] = useState<"idle" | "processing" | "complete" | "error">("idle");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState("Preparing comparative runs...");
  const [progressPercent, setProgressPercent] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Results
  const [results, setResults] = useState<ComparisonRunResult[] | null>(null);
  const [activeGanttAlgo, setActiveGanttAlgo] = useState<string>("");

  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  // Handle file select
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0];
      if (f.name.endsWith(".xlsx") || f.name.endsWith(".xls")) {
        setFile(f);
      }
    }
  };

  const toggleAlgo = (name: keyof typeof algos) => {
    setAlgos(prev => ({ ...prev, [name]: !prev[name] }));
  };

  const startComparison = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const selectedAlgos = Object.entries(algos)
      .filter(([_, checked]) => checked)
      .map(([name]) => name)
      .join(",");

    if (!selectedAlgos) {
      setErrorMsg("Please select at least one algorithm to run.");
      return;
    }

    setStatus("processing");
    setProgressPercent(0);
    setProgressMessage("Uploading dataset...");
    setErrorMsg(null);
    setResults(null);

    try {
      const response = await runComparison(file, {
        setup_time: setupTime,
        algorithms: selectedAlgos,
        pop_size: popSize,
        generations: generations,
        mutation_rate: mutationRate,
        w_makespan: wMakespan,
        w_tardiness: wTardiness
      });

      setTaskId(response.task_id);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to launch comparative simulation.");
      setStatus("error");
    }
  };

  // Poll comparative status
  useEffect(() => {
    if (!taskId) return;

    let ws: WebSocket | null = null;
    let pollInterval: NodeJS.Timeout | null = null;
    let isMounted = true;

    const startHttpPolling = () => {
      console.log("Compare WS: Falling back to HTTP polling...");
      const poll = async () => {
        try {
          const res = await getCompareStatus(taskId);
          if (!isMounted) return;

          if (res.state === "complete") {
            setResults(res.results);
            if (res.results && res.results.length > 0) {
              // Set the best one as initial Gantt selection
              const best = res.results.reduce((prev, current) => 
                (prev.makespan < current.makespan) ? prev : current
              );
              setActiveGanttAlgo(best.algorithm);
            }
            setStatus("complete");
            if (pollInterval) clearInterval(pollInterval);
          } else if (res.state === "error") {
            setErrorMsg(res.message || "Simulation failed.");
            setStatus("error");
            if (pollInterval) clearInterval(pollInterval);
          } else {
            setProgressMessage(res.message || "Simulating algorithms...");
          }
        } catch (err) {
          if (!isMounted) return;
          setErrorMsg(err instanceof Error ? err.message : "Failed to fetch status.");
          setStatus("error");
          if (pollInterval) clearInterval(pollInterval);
        }
      };

      poll();
      pollInterval = setInterval(poll, 2000);
    };

    const connectWebSocket = () => {
      try {
        const token = getAccessToken();
        const wsUrl = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
          .replace(/^http/, "ws") + `/api/ws/tasks/${taskId}${token ? `?token=${token}` : ""}`;

        ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === "progress") {
              setProgressPercent(data.percent || 0);
              setProgressMessage(data.message || "Processing...");
            } else if (data.type === "complete") {
              const rList = data.result?.results as ComparisonRunResult[];
              setResults(rList);
              if (rList && rList.length > 0) {
                const best = rList.reduce((prev, current) => 
                  (prev.makespan < current.makespan) ? prev : current
                );
                setActiveGanttAlgo(best.algorithm);
              }
              setStatus("complete");
              if (ws) ws.close();
            } else if (data.type === "error") {
              setErrorMsg(data.message || "Simulation failed.");
              setStatus("error");
              if (ws) ws.close();
            }
          } catch (e) {
            console.error("Failed to parse WS comparison progress:", e);
          }
        };

        ws.onerror = () => {
          if (isMounted) startHttpPolling();
        };

        ws.onclose = (event) => {
          if (event.code !== 1000 && isMounted && statusRef.current !== "complete" && statusRef.current !== "error") {
            startHttpPolling();
          }
        };
      } catch (err) {
        startHttpPolling();
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [taskId]);

  const resetWorkspace = () => {
    setFile(null);
    setTaskId(null);
    setResults(null);
    setStatus("idle");
    setErrorMsg(null);
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 1280, color: "#fff" }}>
      {/* Header */}
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "1.75rem", fontWeight: 700, marginBottom: 4, display: "flex", alignItems: "center", gap: 10 }}>
          <Zap size={24} style={{ color: "var(--accent)" }} />
          Optimization & Simulation Workspace
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9375rem" }}>
          Upload production job shop schedules and compare makespan, tardiness, and utilization metrics across algorithms.
        </p>
      </div>

      {status === "idle" && (
        <form onSubmit={startComparison} style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Main Layout Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
            
            {/* Left Column: File upload & Setup Time */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              
              {/* File Upload Box */}
              <div className="card" style={{ padding: 24 }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 12 }}>1. Select Production Dataset</h3>
                <div
                  onDragOver={handleDragOver}
                  onDrop={handleDrop}
                  style={{
                    border: "2px dashed var(--border)",
                    borderRadius: "var(--radius-lg)",
                    padding: "32px 20px",
                    textAlign: "center",
                    cursor: "pointer",
                    background: "rgba(255,255,255,0.01)",
                    transition: "all var(--transition-fast)",
                  }}
                >
                  <input
                    type="file"
                    id="optimize-file-input"
                    accept=".xlsx, .xls"
                    onChange={handleFileChange}
                    style={{ display: "none" }}
                  />
                  <label htmlFor="optimize-file-input" style={{ cursor: "pointer", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                    {file ? (
                      <>
                        <FileSpreadsheet size={40} style={{ color: "var(--success)" }} />
                        <div>
                          <p style={{ fontSize: "0.875rem", fontWeight: 600 }}>{file.name}</p>
                          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            {(file.size / 1024).toFixed(1)} KB · Click to change
                          </p>
                        </div>
                      </>
                    ) : (
                      <>
                        <Upload size={40} style={{ color: "var(--text-muted)", opacity: 0.6 }} />
                        <div>
                          <p style={{ fontSize: "0.875rem", fontWeight: 500 }}>
                            Drag and drop Excel here, or <span style={{ color: "var(--secondary)", fontWeight: 600 }}>Browse</span>
                          </p>
                          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>
                            Accepts .xlsx and .xls workbook files
                          </p>
                        </div>
                      </>
                    )}
                  </label>
                </div>
              </div>

              {/* Basic Parameters */}
              <div className="card" style={{ padding: 24 }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>2. Basic Constraints</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: "0.8125rem", fontWeight: 500, color: "var(--text-secondary)" }}>
                    Machine Setup Time (Time Units)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="60"
                    value={setupTime}
                    onChange={(e) => setSetupTime(parseInt(e.target.value) || 0)}
                    className="input"
                    style={{ height: 42 }}
                  />
                  <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 2 }}>
                    Added when a machine changes from processing one job to another.
                  </p>
                </div>
              </div>

            </div>

            {/* Right Column: Algorithms & GA parameters */}
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              
              {/* Algorithm checkboxes */}
              <div className="card" style={{ padding: 24 }}>
                <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 12 }}>3. Choose Algorithms to Compare</h3>
                <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginBottom: 16 }}>
                  Select the strategies you want to run side-by-side on this dataset.
                </p>
                
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  {Object.entries(algos).map(([name, checked]) => (
                    <button
                      key={name}
                      type="button"
                      onClick={() => toggleAlgo(name as keyof typeof algos)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "12px 14px",
                        background: checked ? "rgba(37,99,235,0.08)" : "rgba(255,255,255,0.02)",
                        border: checked ? "1px solid var(--secondary)" : "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "var(--radius-md)",
                        color: checked ? "var(--text-primary)" : "var(--text-secondary)",
                        cursor: "pointer",
                        fontSize: "0.875rem",
                        fontWeight: checked ? 600 : 400,
                        transition: "all var(--transition-fast)",
                      }}
                    >
                      <span>{name}</span>
                      <div style={{
                        width: 18,
                        height: 18,
                        borderRadius: 4,
                        border: "1px solid",
                        borderColor: checked ? "var(--secondary)" : "rgba(255,255,255,0.2)",
                        background: checked ? "var(--secondary)" : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}>
                        {checked && <Check size={12} color="#fff" />}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* GA Parameter Panel (conditional on GA checked) */}
              {algos.GA && (
                <div className="card" style={{ padding: 24 }}>
                  <div 
                    onClick={() => setShowGAParams(!showGAParams)}
                    style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }}
                  >
                    <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>4. Evolutionary Algorithm Settings</h3>
                    <span style={{ fontSize: "0.75rem", color: "var(--secondary)" }}>
                      {showGAParams ? "Hide settings" : "Show settings"}
                    </span>
                  </div>

                  {showGAParams && (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <label style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Pop Size</label>
                          <input type="number" value={popSize} onChange={e => setPopSize(parseInt(e.target.value) || 5)} className="input" style={{ height: 38 }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <label style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Generations</label>
                          <input type="number" value={generations} onChange={e => setGenerations(parseInt(e.target.value) || 5)} className="input" style={{ height: 38 }} />
                        </div>
                      </div>

                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <label style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                          Mutation Rate ({mutationRate * 100}%)
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="0.5"
                          step="0.01"
                          value={mutationRate}
                          onChange={(e) => setMutationRate(parseFloat(e.target.value))}
                          style={{ accentColor: "var(--secondary)", cursor: "pointer" }}
                        />
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <label style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Makespan Weight ({wMakespan})</label>
                          <input type="number" step="0.1" value={wMakespan} onChange={e => setWMakespan(parseFloat(e.target.value) || 0)} className="input" style={{ height: 38 }} />
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                          <label style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Tardiness Weight ({wTardiness})</label>
                          <input type="number" step="0.1" value={wTardiness} onChange={e => setWTardiness(parseFloat(e.target.value) || 0)} className="input" style={{ height: 38 }} />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>

          </div>

          {errorMsg && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: 14, background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "var(--radius-md)", color: "var(--error)", fontSize: "0.875rem" }}>
              <AlertTriangle size={16} />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Action Trigger Button */}
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!file}
            id="optimize-run-btn"
            style={{
              width: "100%",
              height: 48,
              justifyContent: "center",
              fontSize: "0.9375rem",
              fontWeight: 600,
            }}
          >
            <Zap size={16} />
            Run Comparative Simulation
          </button>
        </form>
      )}

      {/* Processing Status Page */}
      {status === "processing" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "80px 24px" }}>
          <div className="card" style={{ maxWidth: 540, width: "100%", textAlign: "center", padding: 40 }}>
            <Loader2 size={40} className="animate-spin" style={{ color: "var(--secondary)", margin: "0 auto 20px" }} />
            <h3 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: 8 }}>Simulating Algorithms</h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginBottom: 24 }}>
              {progressMessage}
            </p>
            
            {/* Progress bar */}
            <div style={{ height: 8, width: "100%", background: "var(--bg-secondary)", borderRadius: 99, overflow: "hidden", position: "relative", marginBottom: 12 }}>
              <div style={{
                width: `${progressPercent}%`,
                height: "100%",
                background: "linear-gradient(90deg, var(--primary), var(--secondary))",
                borderRadius: 99,
                transition: "width 0.4s ease",
              }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-muted)" }}>
              <span>Running simulation...</span>
              <span>{progressPercent}% Complete</span>
            </div>
          </div>
        </div>
      )}

      {/* Completed Results View */}
      {status === "complete" && results && (
        <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          
          {/* Quick Summary Grid */}
          <div className="card" style={{ padding: 24 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <h2 style={{ fontSize: "1.125rem", fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                <BarChart3 size={18} />
                Comparative Summary Metrics
              </h2>
              <button onClick={resetWorkspace} className="btn btn-secondary btn-sm" style={{ gap: 6, height: 32 }}>
                <RefreshCw size={12} />
                Run Another
              </button>
            </div>
            
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--bg-secondary)" }}>
                    {["Algorithm", "Makespan (units)", "Total Tardiness (units)", "Avg Flow Time", "On-Time Ratio", "Actions"].map((col) => (
                      <th key={col} style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600, color: "var(--text-secondary)" }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.map((r, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={{ padding: "12px 16px", fontWeight: 700, color: "var(--secondary)" }}>{r.algorithm}</td>
                      <td style={{ padding: "12px 16px", fontFamily: "monospace" }}>{r.makespan}</td>
                      <td style={{ padding: "12px 16px", fontFamily: "monospace" }}>{r.total_tardiness}</td>
                      <td style={{ padding: "12px 16px", fontFamily: "monospace" }}>{r.avg_flow_time.toFixed(1)}</td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 99,
                          fontSize: "0.75rem",
                          fontWeight: 600,
                          background: r.on_time_percent >= 80 ? "rgba(16,185,129,0.12)" : "rgba(245,158,11,0.12)",
                          color: r.on_time_percent >= 80 ? "var(--success)" : "var(--warning)",
                        }}>
                          {r.on_time_percent.toFixed(1)}%
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", gap: 8 }}>
                          {r.excel_url && (
                            <a
                              href={resourceUrl(r.excel_url) || "#"}
                              download
                              className="btn btn-secondary btn-sm"
                              style={{ height: 28, fontSize: "0.75rem", padding: "0 8px", gap: 4 }}
                            >
                              <Download size={10} />
                              Excel
                            </a>
                          )}
                          <button
                            onClick={() => setActiveGanttAlgo(r.algorithm)}
                            className={`btn btn-sm ${activeGanttAlgo === r.algorithm ? "btn-primary" : "btn-ghost"}`}
                            style={{ height: 28, fontSize: "0.75rem", padding: "0 8px" }}
                          >
                            Show Gantt
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Visual Performance Charts */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24 }}>
            
            {/* Recharts chart */}
            <div className="card" style={{ padding: 24 }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 16 }}>Side-by-Side Performance Comparison</h3>
              <ComparisonChart data={results} />
            </div>

            {/* Quick insights card */}
            <div className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                <Info size={16} style={{ color: "var(--secondary)" }} />
                Scheduler Intelligence Insights
              </h3>
              
              <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1, justifyContent: "center" }}>
                {(() => {
                  const bestMakespan = results.reduce((prev, current) => 
                    (prev.makespan < current.makespan) ? prev : current
                  );
                  const bestTardiness = results.reduce((prev, current) => 
                    (prev.total_tardiness < current.total_tardiness) ? prev : current
                  );

                  return (
                    <>
                      <div style={{ background: "rgba(255,255,255,0.02)", padding: 14, borderRadius: "var(--radius-md)" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>MINIMUM MAKESPAN</span>
                        <p style={{ fontSize: "1.125rem", fontWeight: 700, margin: "2px 0 4px", color: "var(--success)" }}>
                          {bestMakespan.algorithm} ({bestMakespan.makespan} units)
                        </p>
                        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                          Achieves the fastest overall completion for the shop floor layout.
                        </p>
                      </div>

                      <div style={{ background: "rgba(255,255,255,0.02)", padding: 14, borderRadius: "var(--radius-md)" }}>
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>LOWEST JOB TARDINESS</span>
                        <p style={{ fontSize: "1.125rem", fontWeight: 700, margin: "2px 0 4px", color: "var(--accent)" }}>
                          {bestTardiness.algorithm} ({bestTardiness.total_tardiness} delay units)
                        </p>
                        <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                          Minimizes missed customer deadlines and priority penalties.
                        </p>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>

          </div>

          {/* Interactive Gantt timeline viewer */}
          {(() => {
            const currentRun = results.find(r => r.algorithm === activeGanttAlgo);
            if (!currentRun) return null;

            return (
              <div className="card" style={{ padding: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <h3 style={{ fontSize: "1rem", fontWeight: 600 }}>Interactive Gantt Timeline</h3>
                    <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
                      Visual schedule generated by the <strong style={{ color: "var(--secondary)" }}>{activeGanttAlgo}</strong> algorithm.
                    </p>
                  </div>
                  
                  {/* Dropdown switcher */}
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>Visualize:</span>
                    <select
                      value={activeGanttAlgo}
                      onChange={e => setActiveGanttAlgo(e.target.value)}
                      className="input"
                      style={{ height: 32, padding: "0 10px", background: "var(--bg-secondary)", fontSize: "0.875rem", width: 140 }}
                    >
                      {results.map(r => (
                        <option key={r.algorithm} value={r.algorithm}>{r.algorithm}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Gantt Chart component */}
                {currentRun.schedule.length > 0 ? (
                  <GanttChart schedule={currentRun.schedule} makespan={currentRun.makespan} />
                ) : (
                  <div style={{ padding: "40px 0", textAlign: "center", color: "var(--text-muted)" }}>
                    No operations in schedule list.
                  </div>
                )}
              </div>
            );
          })()}

        </div>
      )}
    </div>
  );
}
