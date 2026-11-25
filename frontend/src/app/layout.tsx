import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "IoTSynth AI — Signal Intelligence Studio",
  description:
    "Generative AI and cybersecurity workbench for CTGAN synthetic IoT network telemetry generation, statistical quality auditing, and anomaly-detection training.",
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
