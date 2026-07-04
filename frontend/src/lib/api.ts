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

// Rescheduling Types
export interface BreakdownRequest {
  task_id: string;
  machine_id: number;
  downtime_start: number;
  downtime_end: number;
}

export interface RushJobOperation {
  machine_id: number;
  processing_time: number;
}

export interface RushJobSchema {
  job_id: number;
  operations: RushJobOperation[];
  due_date: number;
  priority: number;
}

export interface RushOrderRequest {
  task_id: string;
  rush_job: RushJobSchema;
}

// Analytics Types
export interface AnalyticsSummaryData {
  total_runs: number;
  avg_makespan: number;
  avg_tardiness: number;
  avg_utilization: number;
  avg_on_time_percent: number;
  best_makespan: number;
  best_algorithm: string | null;
}

export interface TrendPoint {
  task_id: string;
  created_at: string;
  algorithm: string | null;
  makespan: number | null;
  total_tardiness: number | null;
  avg_flow_time: number | null;
  on_time_percent: number | null;
}

export interface TrendsResponse {
  points: TrendPoint[];
  total: number;
}

export interface HeatmapCell {
  task_id: string;
  machine_id: number;
  utilization: number;
}

export interface HeatmapResponse {
  cells: HeatmapCell[];
  machines: number[];
  runs: string[];
}

export interface AlgorithmStats {
  algorithm: string;
  run_count: number;
  avg_makespan: number;
  avg_tardiness: number;
  avg_on_time_percent: number;
  best_makespan: number;
}

export interface AlgorithmComparisonResponse {
  algorithms: AlgorithmStats[];
}

export interface TardinessDistributionResponse {
  buckets: string[];
  counts: number[];
  total_jobs: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  // Attach token if present in localStorage
  const headers = new Headers(options.headers || {});
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle Token Expiry (401 Unauthorized) & Auto-Refresh
  if (
    response.status === 401 &&
    path !== "/api/auth/login" &&
    path !== "/api/auth/refresh" &&
    typeof window !== "undefined"
  ) {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${BASE_URL}/api/auth/refresh`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const keyData = await refreshRes.json();
          localStorage.setItem("access_token", keyData.access_token);
          localStorage.setItem("refresh_token", keyData.refresh_token);

          // Retry the request with the new access token
          headers.set("Authorization", `Bearer ${keyData.access_token}`);
          response = await fetch(url, {
            ...options,
            headers,
          });
        } else {
          // Refresh token expired or revoked — clear auth and redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("user_profile");
          window.location.href = "/login";
        }
      } catch (refreshErr) {
        console.error("Auto refresh failed:", refreshErr);
      }
    }
  }

  if (!response.ok) {
    const errorBody = await response.text();
    let errorDetail = errorBody;
    try {
      const parsed = JSON.parse(errorBody);
      errorDetail = parsed.detail || errorBody;
    } catch {
      // Ignore parsing errors
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
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

// ─── Phase 3: Rescheduling API Endpoints ─────────────────────────────────────

/** POST /api/reschedule/breakdown */
export async function rescheduleBreakdown(body: BreakdownRequest): Promise<UploadResponse> {
  return apiFetch<UploadResponse>("/api/reschedule/breakdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** POST /api/reschedule/rush-order */
export async function rescheduleRushOrder(body: RushOrderRequest): Promise<UploadResponse> {
  return apiFetch<UploadResponse>("/api/reschedule/rush-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ─── Phase 3: Analytics API Endpoints ────────────────────────────────────────

/** GET /api/analytics/summary */
export async function getAnalyticsSummary(): Promise<AnalyticsSummaryData> {
  return apiFetch<AnalyticsSummaryData>("/api/analytics/summary");
}

/** GET /api/analytics/trends */
export async function getAnalyticsTrends(limit: number = 20): Promise<TrendsResponse> {
  return apiFetch<TrendsResponse>(`/api/analytics/trends?limit=${limit}`);
}

/** GET /api/analytics/utilization-heatmap */
export async function getUtilizationHeatmap(limit: number = 10): Promise<HeatmapResponse> {
  return apiFetch<HeatmapResponse>(`/api/analytics/utilization-heatmap?limit=${limit}`);
}

/** GET /api/analytics/algorithm-comparison */
export async function getAlgorithmComparison(): Promise<AlgorithmComparisonResponse> {
  return apiFetch<AlgorithmComparisonResponse>("/api/analytics/algorithm-comparison");
}

/**
 * GET /api/analytics/tardiness-distribution
 */
export async function getTardinessDistribution(
  limit: number = 10,
  bucketSize: number = 5
): Promise<TardinessDistributionResponse> {
  return apiFetch<TardinessDistributionResponse>(
    `/api/analytics/tardiness-distribution?limit=${limit}&bucket_size=${bucketSize}`
  );
}

// ─── Authentication API Endpoints ──────────────────────────────────────────

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export async function login(email: string, password: string): Promise<{ access_token: string; refresh_token: string }> {
  const data = await apiFetch<{ access_token: string; refresh_token: string }>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export async function register(email: string, username: string, password: string): Promise<UserProfile> {
  return apiFetch<UserProfile>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, username, password }),
  });
}

export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (refreshToken) {
    try {
      await apiFetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (e) {
      console.error("Logout API call failed:", e);
    }
  }
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user_profile");
}

export async function getCurrentUserProfile(): Promise<UserProfile> {
  const profile = await apiFetch<UserProfile>("/api/auth/me");
  localStorage.setItem("user_profile", JSON.stringify(profile));
  return profile;
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}
