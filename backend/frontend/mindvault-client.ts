// Framework-independent fetch client. No server credentials belong in this file.
export type Finding = {
  id: string; revision_id: string; origin: string; category: string;
  verdict: string; severity: string; confidence: number;
  span_start: number; span_end: number; quoted_text: string;
  explanation: string; suggested_fix: string | null; status: string;
  source: { document_id: string; document_title: string; location: string; excerpt: string } | null;
};
export type ReviewRun = {
  id: string; status: "queued" | "running" | "done" | "failed" | "legacy";
  ai_used: boolean; ai_status: string; issues: string[]; findings: Finding[];
};

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

export class MindVaultClient {
  private token = "";
  constructor(private baseUrl = "http://localhost:8000/api") {}
  setToken(token: string) { this.token = token; }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    if (this.token) headers.set("Authorization", `Bearer ${this.token}`);
    if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    const response = await fetch(this.baseUrl.replace(/\/$/, "") + path, { ...init, headers });
    const data = await response.json();
    if (!response.ok) throw new ApiError(response.status, data.code ?? "request_error", data.detail ?? "Request failed");
    return data as T;
  }

  async demoLogin(role: "admin" | "creator" | "reviewer") {
    const result = await this.request<{ token: string; user: Record<string, unknown> }>(`/auth/demo?role=${role}`, { method: "POST" });
    this.setToken(result.token);
    return result.user;
  }

  startReview(contentId: string) {
    return this.request<{ run_id: string }>(`/content/${encodeURIComponent(contentId)}/review`, { method: "POST" });
  }

  async waitForReview(runId: string, signal?: AbortSignal): Promise<ReviewRun> {
    const deadline = Date.now() + 195_000;
    while (Date.now() < deadline) {
      signal?.throwIfAborted();
      const requestSignal = signal ? AbortSignal.any([signal, AbortSignal.timeout(15_000)]) : AbortSignal.timeout(15_000);
      const run = await this.request<ReviewRun>(`/review-runs/${encodeURIComponent(runId)}`, { signal: requestSignal });
      if (["done", "failed", "legacy"].includes(run.status)) return run;
      await new Promise<void>((resolve, reject) => {
        const onAbort = () => { clearTimeout(timer); reject(signal?.reason); };
        const timer = setTimeout(() => { signal?.removeEventListener("abort", onAbort); resolve(); }, 1500);
        signal?.addEventListener("abort", onAbort, { once: true });
      });
    }
    throw new ApiError(408, "poll_timeout", "Review is taking too long. Refresh its status before retrying.");
  }

  decide(findingId: string, decision: { action: "accept" | "edit" | "reject" | "dismiss"; edited_text?: string; note?: string }) {
    return this.request<Finding>(`/findings/${encodeURIComponent(findingId)}/decision`, { method: "POST", body: JSON.stringify(decision) });
  }
}

export function findingSegments(text: string, finding: Pick<Finding, "span_start" | "span_end" | "quoted_text">) {
  const chars = Array.from(text);
  const { span_start: start, span_end: end } = finding;
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end < start || end > chars.length || chars.slice(start, end).join("") !== finding.quoted_text)
    throw new Error("Finding belongs to a different revision or has invalid offsets.");
  return { before: chars.slice(0, start).join(""), quote: chars.slice(start, end).join(""),
    after: chars.slice(end).join(""), insertion: start === end };
}
