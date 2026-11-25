"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ToastProvider } from "@/components/ui/ToastProvider";
import { AppHeader } from "./layout/AppHeader";
import { AppSidebar } from "./layout/AppSidebar";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [online, setOnline] = useState<boolean | null>(null);
  const [counts, setCounts] = useState<{ ctgan: number | null; anomaly: number | null }>({
    ctgan: null,
    anomaly: null,
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const [hRes, mRes] = await Promise.allSettled([
          api.getHealth(),
          api.getSystemModelsStatus(),
        ]);
        if (!active) return;
        if (hRes.status === "fulfilled") {
          setOnline(hRes.value.status === "healthy");
        } else {
          setOnline(false);
        }
        if (mRes.status === "fulfilled" && mRes.value) {
          setCounts({
            ctgan: mRes.value.ctgan_models_count ?? null,
            anomaly: mRes.value.anomaly_models_count ?? null,
          });
        }
      } catch {
        if (active) setOnline(false);
      }
    };
    poll();
    const timer = setInterval(poll, 25000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <ToastProvider>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-xs focus:font-bold focus:text-white"
      >
        Skip to main content
      </a>

      <div className="flex min-h-screen bg-canvas text-ink">
        <AppSidebar
          online={online}
          ctganCount={counts.ctgan}
          anomalyCount={counts.anomaly}
          mobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
        />

        <div className="flex min-w-0 flex-1 flex-col">
          <AppHeader online={online} onOpenMobileMenu={() => setMobileOpen(true)} />
          <main
            id="main-content"
            className="mx-auto w-full max-w-[1520px] flex-1 px-4 py-6 sm:px-6 lg:px-8"
          >
            {children}
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
