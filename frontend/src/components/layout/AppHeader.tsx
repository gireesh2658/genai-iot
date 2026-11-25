"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { BrandMark, NAV_ROUTES } from "./AppSidebar";
import { IconButton } from "@/components/ui/Button";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

export function AppHeader({
  online,
  onOpenMobileMenu,
}: {
  online: boolean | null;
  onOpenMobileMenu: () => void;
}) {
  const pathname = usePathname();
  const activeRoute =
    NAV_ROUTES.find((r) => (r.href === "/" ? pathname === "/" : pathname.startsWith(r.href))) ||
    NAV_ROUTES[0];

  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1520px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <IconButton
            label="Open navigation menu"
            onClick={onOpenMobileMenu}
            className="min-h-[44px] min-w-[44px] border-hairline lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </IconButton>

          <Link href="/" className="flex items-center gap-2 lg:hidden">
            <BrandMark />
            <span className="text-sm font-bold text-ink">IoTSynth AI</span>
          </Link>

          <nav aria-label="Breadcrumb" className="hidden min-w-0 items-center gap-2 text-xs lg:flex">
            <span className="rounded-md border border-hairline bg-well px-2 py-0.5 font-semibold text-ink-secondary">
              Cybersecurity (IoT)
            </span>
            <span className="text-ink-muted" aria-hidden="true">
              /
            </span>
            <span className="font-bold text-ink">{activeRoute.label}</span>
            <span className="hidden text-ink-secondary xl:inline">· {activeRoute.caption}</span>
          </nav>
        </div>

        <div className="flex items-center gap-2.5">
          <span className="hidden rounded-full border border-hairline bg-well px-3 py-1 font-mono text-[11px] font-medium text-ink-secondary sm:inline-flex">
            CICIoT2023 · 44-Col Telemetry · CPU PyTorch
          </span>
          {online === false && <StatusIndicator tone="danger" label="API Unreachable" />}
        </div>
      </div>
    </header>
  );
}
