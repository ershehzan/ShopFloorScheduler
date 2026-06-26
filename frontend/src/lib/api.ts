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

export interface ScheduleRunSummary {
  task_id: string;
  created_at: string;
  status: "pending" | "processing" | "complete" | "error";
  algorithm: string | null;
  file_name: string | null;
  makespan: number | null;
  total_tardiness: number | null;
  avg_flow_time: number | null;
  on_time_percent: number | null;
}

export interface HistoryResponse {
  items: ScheduleRunSummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
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

/** GET /api/history — paginated schedule run history */
export async function getHistory(params: {
  page?: number;
  page_size?: number;
  algorithm?: string;
  status?: string;
} = {}): Promise<HistoryResponse> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.page_size) query.set("page_size", String(params.page_size));
  if (params.algorithm) query.set("algorithm", params.algorithm);
  if (params.status) query.set("status", params.status);
  const qs = query.toString();
  return apiFetch<HistoryResponse>(`/api/history${qs ? "?" + qs : ""}`);
}
