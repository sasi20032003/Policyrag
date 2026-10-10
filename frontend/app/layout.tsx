import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "PolicyGraph-RAG · Next-Gen Healthcare Insurance Navigation",
  description: "Temporal, Contradiction-Aware, and Evidence-Verified RAG with Zero-Hallucination Guard and Conformal Risk Calibration.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="bg-slate-950 text-slate-100 antialiased selection:bg-cyan-500/30 selection:text-white">
        <div className="relative flex min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-[#060913]">
          {/* Ambient luminous glow background orbs */}
          <div className="pointer-events-none fixed -top-40 left-60 h-[500px] w-[500px] rounded-full bg-cyan-500/10 blur-[130px]" />
          <div className="pointer-events-none fixed top-1/3 -right-40 h-[600px] w-[600px] rounded-full bg-purple-600/10 blur-[150px]" />
          <div className="pointer-events-none fixed -bottom-40 left-1/3 h-[500px] w-[500px] rounded-full bg-emerald-500/08 blur-[140px]" />

          {/* Main navigation sidebar */}
          <Sidebar />

          {/* Page contents */}
          <main className="relative flex-1 overflow-x-hidden min-h-screen">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
