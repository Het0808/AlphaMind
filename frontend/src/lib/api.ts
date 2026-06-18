// Typed client for the AlphaMind FastAPI backend.
// Every call falls back to mock data when the backend is unset or unreachable,
// so the UI is fully demonstrable offline.

import {
  mockCitations, mockDebate, mockEval, mockReport, mockSnapshot,
} from "./mock";
import type {
  Citation, DebateResult, EvalReport, FinancialSnapshot, InvestmentReport,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "";

export const usingMock = !BASE;

async function post<T>(path: string, body: unknown, fallback: T): Promise<{ data: T; mocked: boolean }> {
  if (!BASE) return { data: fallback, mocked: true };
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { data: (await res.json()) as T, mocked: false };
  } catch {
    return { data: fallback, mocked: true };
  }
}

async function get<T>(path: string, fallback: T): Promise<{ data: T; mocked: boolean }> {
  if (!BASE) return { data: fallback, mocked: true };
  try {
    const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { data: (await res.json()) as T, mocked: false };
  } catch {
    return { data: fallback, mocked: true };
  }
}

export const api = {
  analyze: (ticker: string, opts?: { horizon?: string }) =>
    post<InvestmentReport>("/analyze", { ticker, horizon: opts?.horizon ?? "12 months" }, { ...mockReport, ticker }),

  debate: (ticker: string, rounds = 2) =>
    post<DebateResult>("/debate", { ticker, rounds }, { ...mockDebate, ticker }),

  // The backend exposes financials through /analyze; the UI also keeps a direct
  // snapshot path for the Financial Dashboard, mocked until a /snapshot route exists.
  snapshot: (ticker: string) =>
    get<FinancialSnapshot>(`/snapshot/${ticker}`, { ...mockSnapshot, ticker }),

  filingsSearch: (ticker: string, query: string) =>
    post<{ results: Citation[] }>("/filings/search", { ticker, query }, { results: mockCitations }),

  evalReport: () => get<EvalReport>("/eval/report", mockEval),
};
