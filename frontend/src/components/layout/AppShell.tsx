"use client";

import * as React from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/** Responsive shell: fixed sidebar on desktop, slide-over drawer on mobile. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar onMenu={() => setMobileOpen(true)} />
        <main className="scroll-thin grid-bg flex-1 overflow-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
