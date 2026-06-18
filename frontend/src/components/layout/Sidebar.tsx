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

export function Sidebar({ mobileOpen = false, onClose }: { mobileOpen?: boolean; onClose?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden" onClick={onClose} aria-hidden />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border/70 bg-card/70 backdrop-blur-xl transition-transform duration-300 md:static md:z-auto md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-14 items-center gap-2.5 border-b border-border/70 px-4">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-primary to-[hsl(168_70%_40%)] text-primary-foreground shadow-lg shadow-primary/20">
            <BarChart3 className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold tracking-tight">AlphaMind</div>
            <div className="text-[10px] text-muted-foreground">Research Terminal</div>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 p-2.5">
          <div className="label px-2 pb-1.5 pt-1">Workspace</div>
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                onClick={onClose}
                className={cn(
                  "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all",
                  active
                    ? "bg-primary/12 font-medium text-primary"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                {active && <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary" />}
                <Icon className={cn("h-4 w-4 shrink-0 transition-transform group-hover:scale-110", active && "text-primary")} />
                <span className="truncate">{label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border/70 p-3">
          <div className="flex items-center gap-2 rounded-lg bg-muted/40 px-3 py-2 text-[11px] text-muted-foreground">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-bull/60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-bull" />
            </span>
            Agents online · v0.1
          </div>
        </div>
      </aside>
    </>
  );
}
