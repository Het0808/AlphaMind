"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity, BarChart3, Brain, FlaskConical, LineChart, Briefcase, Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/research", label: "Research Workspace", icon: Activity },
  { href: "/company", label: "Company Analysis", icon: Building2 },
  { href: "/reasoning", label: "Agent Reasoning", icon: Brain },
  { href: "/financials", label: "Financial Dashboard", icon: LineChart },
  { href: "/portfolio", label: "Portfolio Advisor", icon: Briefcase },
  { href: "/evaluation", label: "Evaluation", icon: FlaskConical },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-card">
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <div className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
          <BarChart3 className="h-4 w-4" />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight">AlphaMind</div>
          <div className="text-[10px] text-muted-foreground">Research Terminal</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active ? "bg-primary/15 font-medium text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-3 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-bull" />
          Agents online · v0.1
        </div>
      </div>
    </aside>
  );
}
