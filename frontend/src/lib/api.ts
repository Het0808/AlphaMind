// Typed client for the AlphaMind FastAPI backend.
// With NEXT_PUBLIC_API_URL set, calls hit the live backend (/v1/*). Otherwise
// they fall back to ticker-AWARE demo data, so the dashboard still changes per
// company. Every step is logged to the console for auditability.

import {
  mockCitationsFor, mockDebateFor, mockEval, mockReportFor, mockSnapshotFor,
} from "./mock";
import type {
  Citation, DebateResult, EvalReport, FinancialSnapshot, InvestmentReport,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

export const usingMock = !BASE;

function log(...args: unknown[]) {
  if (typeof window !== "undefined") console.info("%c[alphamind:api]", "color:#19d27c", ...args);
}

async function post<T>(path: string, body: unknown, fallback: () => T): Promise<{ data: T; mocked: boolean }> {
  log("POST", path, body, "·", BASE ? `live → ${BASE}` : "mock mode");
  if (!BASE) { const data = fallback(); log("← mock response for", path); return { data, mocked: true }; }
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as T;
    log("← live response for", path);
    return { data, mocked: false };
  } catch (e) {
    log("live request failed, falling back to mock:", String(e));
    return { data: fallback(), mocked: true };
  }
}

async function get<T>(path: string, fallback: () => T): Promise<{ data: T; mocked: boolean }> {
  log("GET", path, "·", BASE ? `live → ${BASE}` : "mock mode");
  if (!BASE) { const data = fallback(); log("← mock response for", path); return { data, mocked: true }; }
  try {
    const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as T;
    log("← live response for", path);
    return { data, mocked: false };
  } catch (e) {
    log("live request failed, falling back to mock:", String(e));
    return { data: fallback(), mocked: true };
  }
}

export const api = {
  analyze: (ticker: string, opts?: { horizon?: string }) =>
    post<InvestmentReport>("/v1/analyze", { ticker, horizon: opts?.horizon ?? "12 months" },
      () => mockReportFor(ticker)),

  debate: (ticker: string, rounds = 2) =>
    post<DebateResult>("/v1/debate", { ticker, rounds }, () => mockDebateFor(ticker)),

  snapshot: (ticker: string) =>
    get<FinancialSnapshot>(`/v1/snapshot/${encodeURIComponent(ticker)}`, () => mockSnapshotFor(ticker)),

  filingsSearch: (ticker: string, query: string) =>
    post<{ results: Citation[] }>("/v1/filings/search", { ticker, query }, () => ({ results: mockCitationsFor(ticker) })),

  evalReport: () => get<EvalReport>("/eval/report", () => mockEval),
};
