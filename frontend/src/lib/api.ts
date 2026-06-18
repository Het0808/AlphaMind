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

// Minimal client-side name map so the demo (no-backend) shows the right company
// identity for the requested ticker rather than always the example fixture's.
const COMPANY_NAMES: Record<string, string> = {
  AAPL: "Apple Inc.", MSFT: "Microsoft Corporation", TSLA: "Tesla, Inc.",
  NVDA: "NVIDIA Corporation", GOOGL: "Alphabet Inc.", AMZN: "Amazon.com, Inc.",
  META: "Meta Platforms, Inc.", AMD: "Advanced Micro Devices, Inc.",
  "RELIANCE.NS": "Reliance Industries Limited", "INFY.NS": "Infosys Limited",
  "TCS.NS": "Tata Consultancy Services Limited",
};
const nameFor = (ticker: string) => COMPANY_NAMES[ticker.toUpperCase()] ?? ticker.toUpperCase();

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
    post<InvestmentReport>("/v1/analyze", { ticker, horizon: opts?.horizon ?? "12 months" },
      { ...mockReport, ticker: ticker.toUpperCase(), company_name: nameFor(ticker) }),

  debate: (ticker: string, rounds = 2) =>
    post<DebateResult>("/v1/debate", { ticker, rounds },
      { ...mockDebate, ticker: ticker.toUpperCase(), company_name: nameFor(ticker) }),

  // The backend exposes financials through /v1/analyze; the UI also keeps a direct
  // snapshot path for the Financial Dashboard, mocked until a /snapshot route exists.
  snapshot: (ticker: string) =>
    get<FinancialSnapshot>(`/snapshot/${ticker}`,
      { ...mockSnapshot, ticker: ticker.toUpperCase(),
        overview: { ...mockSnapshot.overview, ticker: ticker.toUpperCase(), name: nameFor(ticker) } }),

  filingsSearch: (ticker: string, query: string) =>
    post<{ results: Citation[] }>("/v1/filings/search", { ticker, query }, { results: mockCitations }),

  evalReport: () => get<EvalReport>("/eval/report", mockEval),
};
