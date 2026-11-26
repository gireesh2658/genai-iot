import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "IoTSynth AI — Synthetic IoT Traffic Generator",
  description:
    "Generate device-aware synthetic normal and attack IoT network traffic using CTGAN V2 for anomaly detection evaluation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <body className="min-h-screen bg-[#F6F8F5] font-sans text-[#2B3748] antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
