"use client";

import * as React from "react";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DEFAULT_TICKER } from "@/lib/constants";

export function TickerInput({
  defaultValue = DEFAULT_TICKER, loading, onSubmit,
}: { defaultValue?: string; loading?: boolean; onSubmit: (ticker: string) => void }) {
  const [value, setValue] = React.useState(defaultValue);
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSubmit(value.trim());   // backend resolves names or symbols
      }}
    >
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ticker or company…"
          className="mono w-48 pl-8"
        />
      </div>
      <Button type="submit" size="sm" disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Run"}
      </Button>
    </form>
  );
}
