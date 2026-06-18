"use client";

import * as React from "react";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useCompanyStore } from "@/lib/store";

/**
 * Global company search. Reads the selected ticker from the store (so the box on
 * EVERY page shows the current company) and writes the new selection on submit.
 */
export function TickerInput() {
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);
  const loading = useCompanyStore((s) => s.loading);
  const selectCompany = useCompanyStore((s) => s.selectCompany);

  const [value, setValue] = React.useState(selectedTicker);
  // Reflect global selection whenever it changes (e.g. set on another page).
  React.useEffect(() => { setValue(selectedTicker); }, [selectedTicker]);

  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const q = value.trim();
        if (q) {
          console.info("%c[alphamind:ui]", "color:#f5a623", "ticker submitted:", q);
          selectCompany(q);
        }
      }}
    >
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ticker or company…"
          aria-label="Search company"
          className="mono w-48 pl-8"
        />
      </div>
      <Button type="submit" size="sm" disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Run"}
      </Button>
    </form>
  );
}
