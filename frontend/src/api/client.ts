import type {
  ApprovalSubmission,
  CreateRunBody,
  RunDetail,
  RunListResponse,
} from "./types";

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string; message?: string };
      detail = body.detail ?? body.message ?? detail;
    } catch {
      // response was not JSON; keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  createRun(body: CreateRunBody): Promise<RunDetail> {
    return request<RunDetail>("/api/runs", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  listRuns(limit = 20, offset = 0): Promise<RunListResponse> {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    return request<RunListResponse>(`/api/runs?${params.toString()}`);
  },

  getRun(id: string): Promise<RunDetail> {
    return request<RunDetail>(`/api/runs/${encodeURIComponent(id)}`);
  },

  submitApprovals(id: string, body: ApprovalSubmission): Promise<RunDetail> {
    return request<RunDetail>(
      `/api/runs/${encodeURIComponent(id)}/approvals`,
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    );
  },

  eventsUrl(id: string): string {
    return `${API_BASE}/api/runs/${encodeURIComponent(id)}/events`;
  },
};
