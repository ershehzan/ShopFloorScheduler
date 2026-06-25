/**
 * lib/api.ts
 * Typed fetch wrapper for the ShopFloorScheduler FastAPI backend.
 * All API calls go through these helpers so the base URL is configured once.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface UploadResponse {
  task_id: string;
  message: string;
  status_url: string;
}

export interface ScheduledOperation {
  job_id: number;
  op_index: number;
  machine_id: number;
  start_time: number;
  end_time: number;
}

export interface UtilizationEntry {
  machine_id: number;
  utilization: number;
}

export interface ScheduleResultData {
  makespan: number;
  total_tardiness: number;
  avg_flow_time: number;
  on_time_percent: number;
  algorithm: string;
  chart_url: string | null;
  excel_url: string | null;
  schedule: ScheduledOperation[];
  utilization: UtilizationEntry[];
}

export interface StatusResponse {
  task_id: string;
  state: "pending" | "processing" | "complete" | "error";
  message: string;
  result: ScheduleResultData | null;
}

export interface HealthResponse {
  status: string;
  version: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(
      `API error ${response.status} on ${path}: ${errorBody}`
    );
  }
  return response.json() as Promise<T>;
}

// ─── API Functions ───────────────────────────────────────────────────────────

/** GET /health */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}

/** POST /api/schedule/upload */
export async function uploadSchedule(
  file: File,
  params: {
    setup_time?: number;
    algorithm?: string;
    pop_size?: number;
    generations?: number;
    mutation_rate?: number;
    w_makespan?: number;
    w_tardiness?: number;
  }
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) form.append(k, String(v));
  });
  return apiFetch<UploadResponse>("/api/schedule/upload", {
    method: "POST",
    body: form,
  });
}

/** GET /api/schedule/status/{taskId} */
export async function getStatus(taskId: string): Promise<StatusResponse> {
  return apiFetch<StatusResponse>(`/api/schedule/status/${taskId}`);
}

/** GET /api/schedule/results/{taskId} */
export async function getResults(taskId: string): Promise<StatusResponse> {
  return apiFetch<StatusResponse>(`/api/schedule/results/${taskId}`);
}

/** Build an absolute URL for a backend resource (Gantt PNG, Excel download) */
export function resourceUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${BASE_URL}${path}`;
}
