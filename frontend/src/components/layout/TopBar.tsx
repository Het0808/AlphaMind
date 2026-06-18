"use client";

import { usingMock } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

/** Bloomberg-style ticker tape + data-source status. */
export function TopBar() {
  const tape = [
    { s: "NVDA", p: "182.34", c: "+2.1%", up: true },
    { s: "AAPL", p: "238.12", c: "-0.4%", up: false },
    { s: "MSFT", p: "512.88", c: "+0.9%", up: true },
    { s: "S&P", p: "6,012", c: "+0.3%", up: true },
    { s: "BTC", p: "98,420", c: "-1.2%", up: false },
    { s: "10Y", p: "4.18%", c: "+3bp", up: true },
  ];
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4">
      <div className="scroll-thin flex items-center gap-5 overflow-x-auto">
        {tape.map((t) => (
          <div key={t.s} className="flex items-center gap-2 whitespace-nowrap">
            <span className="mono text-xs font-semibold text-muted-foreground">{t.s}</span>
            <span className="mono text-xs">{t.p}</span>
            <span className={`mono text-[10px] ${t.up ? "ticker-up" : "ticker-down"}`}>{t.c}</span>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2">
        {usingMock ? (
          <Badge variant="warn">Demo data</Badge>
        ) : (
          <Badge variant="bull">Live · API</Badge>
        )}
      </div>
    </header>
  );
}
