"use client";

import { Menu } from "lucide-react";
import { usingMock } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { useCurrencyStore } from "@/lib/currency";

/** Bloomberg-style ticker tape + data-source status, with a mobile menu button. */
export function TopBar({ onMenu }: { onMenu?: () => void }) {
  const rate = useCurrencyStore((s) => s.rate);
  const fxSource = useCurrencyStore((s) => s.source);
  const tape = [
    { s: "NVDA", p: "182.34", c: "+2.1%", up: true },
    { s: "AAPL", p: "238.12", c: "-0.4%", up: false },
    { s: "MSFT", p: "512.88", c: "+0.9%", up: true },
    { s: "S&P", p: "6,012", c: "+0.3%", up: true },
    { s: "BTC", p: "98,420", c: "-1.2%", up: false },
    { s: "10Y", p: "4.18%", c: "+3bp", up: true },
  ];
  return (
    <header className="flex h-14 items-center justify-between gap-3 border-b border-border/70 bg-card/60 px-3 backdrop-blur-xl sm:px-4">
      <div className="flex min-w-0 items-center gap-3">
        <button
          onClick={onMenu}
          aria-label="Open navigation"
          className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground md:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="scroll-thin flex items-center gap-5 overflow-x-auto">
          {tape.map((t) => (
            <div key={t.s} className="flex items-center gap-2 whitespace-nowrap">
              <span className="mono text-xs font-semibold text-muted-foreground">{t.s}</span>
              <span className="mono text-xs">{t.p}</span>
              <span className={`mono text-[10px] ${t.up ? "ticker-up" : "ticker-down"}`}>{t.c}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Badge variant="info" title={`USD→INR (${fxSource})`} className="mono hidden sm:inline-flex">
          USD/INR ₹{rate.toFixed(2)}
        </Badge>
        {usingMock ? <Badge variant="warn">Demo data</Badge> : <Badge variant="bull">Live · API</Badge>}
      </div>
    </header>
  );
}
