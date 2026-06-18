"use client";

// Currency Service: USD/INR exchange rate with caching, auto-refresh and a
// safe fallback. Backed by a Zustand store persisted to localStorage.

import { create } from "zustand";
import { persist, createJSONStorage, type StateStorage } from "zustand/middleware";
import { DEFAULT_USD_INR } from "./currency-format";

export * from "./currency-format";

const TTL_MS = 6 * 60 * 60 * 1000; // refresh at most every 6h
const RATE_URL = "https://open.er-api.com/v6/latest/USD";

interface CurrencyState {
  rate: number;
  updatedAt: number | null;
  source: "fallback" | "live" | "cache";
  refresh: (force?: boolean) => Promise<void>;
}

const noopStorage: StateStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };

export const useCurrencyStore = create<CurrencyState>()(
  persist(
    (set, get) => ({
      rate: DEFAULT_USD_INR,
      updatedAt: null,
      source: "fallback",

      refresh: async (force = false) => {
        const { updatedAt } = get();
        if (!force && updatedAt && Date.now() - updatedAt < TTL_MS) {
          return; // cached rate is still fresh
        }
        try {
          const res = await fetch(RATE_URL, { cache: "no-store" });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          const inr = data?.rates?.INR;
          if (typeof inr !== "number" || inr <= 0) throw new Error("INR rate missing");
          set({ rate: inr, updatedAt: Date.now(), source: "live" });
          if (typeof window !== "undefined")
            console.info("%c[alphamind:currency]", "color:#19d27c", "USD/INR refreshed →", inr);
        } catch (e) {
          // Fallback: keep any cached rate; otherwise use the constant default.
          if (typeof window !== "undefined")
            console.warn("[alphamind:currency] refresh failed, using fallback:", String(e));
          if (!get().updatedAt) set({ rate: DEFAULT_USD_INR, source: "fallback" });
        }
      },
    }),
    {
      name: "alphamind:fx",
      storage: createJSONStorage((): StateStorage => (typeof window !== "undefined" ? localStorage : noopStorage)),
      partialize: (s) => ({ rate: s.rate, updatedAt: s.updatedAt, source: s.source }),
    },
  ),
);
