import type { ResolvedTarget, SurveyCatalog } from "../types";

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { signal, headers: { Accept: "application/json" } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function resolveTarget(query: string, opts?: { refresh?: boolean; signal?: AbortSignal }) {
  const params = new URLSearchParams({ q: query });
  if (opts?.refresh) params.set("refresh", "true");
  return getJson<ResolvedTarget>(`/api/resolve?${params.toString()}`, opts?.signal);
}

export function fetchSurveyCatalog(signal?: AbortSignal) {
  return getJson<SurveyCatalog>("/api/surveys", signal);
}
