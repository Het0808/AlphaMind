"use client";

import * as React from "react";
import { Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export function TickerInput({
  defaultValue = "NVDA", loading, onSubmit,
}: { defaultValue?: string; loading?: boolean; onSubmit: (ticker: string) => void }) {
  const [value, setValue] = React.useState(defaultValue);
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSubmit(value.trim().toUpperCase());
      }}
    >
      <div className="relative">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ticker…"
          className="mono w-40 pl-8 uppercase"
        />
      </div>
      <Button type="submit" size="sm" disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Run"}
      </Button>
    </form>
  );
}
