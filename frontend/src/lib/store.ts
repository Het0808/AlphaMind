"use client";

// Global application state: the selected company is the single source of truth
// for EVERY page. Persisted to localStorage so navigation and refresh never reset
// it. Selecting a company fetches analysis + financials + debate once and shares
// the results across the whole app.

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { api } from "./api";
import { DEFAULT_TICKER } from "./constants";
import type { DebateResult, FinancialSnapshot, InvestmentReport } from "./types";

interface CompanyState {
  // ── selection ──
  selectedTicker: string;
  selectedCompany: string;
  // ── shared results ──
  analysisData: InvestmentReport | null;
  financialData: FinancialSnapshot | null;
  debateData: DebateResult | null;
  // ── status ──
  loading: boolean;
  error: string | null;
  mocked: boolean;
  lastUpdated: number | null;
  hydrated: boolean;
  // ── actions ──
  selectCompany: (query: string) => Promise<void>;
  bootstrap: () => void;
  setHydrated: () => void;
}

function log(...args: unknown[]) {
  if (typeof window !== "undefined") console.info("%c[alphamind:store]", "color:#19d27c;font-weight:bold", ...args);
}

export const useCompanyStore = create<CompanyState>()(
  persist(
    (set, get) => ({
      selectedTicker: "",
      selectedCompany: "",
      analysisData: null,
      financialData: null,
      debateData: null,
      loading: false,
      error: null,
      mocked: false,
      lastUpdated: null,
      hydrated: false,

      selectCompany: async (query: string) => {
        const q = (query ?? "").trim();
        if (!q || get().loading) return;
        log("selectCompany →", q);
        set({ loading: true, error: null });
        try {
          const [a, f, d] = await Promise.all([api.analyze(q), api.snapshot(q), api.debate(q)]);
          const selectedTicker = a.data.ticker;
          const selectedCompany = a.data.company_name;
          set({
            selectedTicker, selectedCompany,
            analysisData: a.data, financialData: f.data, debateData: d.data,
            loading: false, mocked: a.mocked, lastUpdated: Date.now(),
          });
          log("Current Company:", selectedCompany, "| Current Ticker:", selectedTicker, "| live:", !a.mocked);
        } catch (e) {
          log("selectCompany FAILED:", String(e));
          set({ loading: false, error: String(e) });
        }
      },

      // On first load (after hydration): if nothing is selected, use the
      // configured default (env-driven, not a hardcoded company).
      bootstrap: () => {
        const { selectedTicker, loading } = get();
        if (!selectedTicker && !loading && DEFAULT_TICKER) {
          get().selectCompany(DEFAULT_TICKER);
        }
      },

      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "alphamind:selected-company",
      storage: createJSONStorage(() => localStorage),
      // Persist the selection + last results so refresh preserves the company.
      partialize: (s) => ({
        selectedTicker: s.selectedTicker,
        selectedCompany: s.selectedCompany,
        analysisData: s.analysisData,
        financialData: s.financialData,
        debateData: s.debateData,
        lastUpdated: s.lastUpdated,
        mocked: s.mocked,
      }),
      onRehydrateStorage: () => (state) => state?.setHydrated(),
    },
  ),
);
