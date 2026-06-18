"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanyStore } from "@/lib/store";
import { useCurrencyStore } from "@/lib/currency";

/** Responsive shell + global-state bootstrap + route/company debug logging. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [mounted, setMounted] = React.useState(false);

  const bootstrap = useCompanyStore((s) => s.bootstrap);
  const refreshFx = useCurrencyStore((s) => s.refresh);
  const selectedCompany = useCompanyStore((s) => s.selectedCompany);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);
  const pathname = usePathname();

  // Mount gate avoids a hydration mismatch between SSR (empty) and the
  // localStorage-rehydrated client store; bootstraps the company + FX rate.
  React.useEffect(() => { setMounted(true); bootstrap(); refreshFx(); }, [bootstrap, refreshFx]);

  // Debug logging on every navigation.
  React.useEffect(() => {
    if (!mounted) return;
    console.info(
      "%c[alphamind:route]", "color:#38bdf8;font-weight:bold",
      "Current Company:", selectedCompany || "—",
      "| Current Ticker:", selectedTicker || "—",
      "| Current Route:", pathname,
    );
  }, [pathname, selectedCompany, selectedTicker, mounted]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar onMenu={() => setMobileOpen(true)} />
        <main className="scroll-thin grid-bg flex-1 overflow-auto p-4 sm:p-6">
          {mounted ? children : (
            <div className="mx-auto max-w-7xl space-y-4">
              <Skeleton className="h-10 w-64" />
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
