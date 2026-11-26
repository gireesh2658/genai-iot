"use client";

import React from "react";
import { AppHeader } from "./layout/AppHeader";

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-xs focus:font-bold focus:text-white"
      >
        Skip to main content
      </a>

      <AppHeader />

      <main
        id="main-content"
        className="mx-auto w-full max-w-[1360px] flex-1 px-4 py-6 sm:px-6 lg:px-8"
      >
        {children}
      </main>
    </div>
  );
}
