"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  HomeIcon,
  ChatIcon,
  CompareIcon,
  NetworkIcon,
  BookOpenIcon,
  UserIcon,
  UploadIcon,
  AdminIcon,
  ShieldCheckIcon,
  SparklesIcon,
} from "./Icons";
import { getHealth } from "@/services/api";

const NAV_ITEMS = [
  {
    href: "/",
    label: "Overview",
    desc: "Command Center",
    icon: HomeIcon,
    color: "from-cyan-500 to-blue-500",
    badge: null,
  },
  {
    href: "/chat",
    label: "AI Research Assistant",
    desc: "Agentic RAG & SSE",
    icon: ChatIcon,
    color: "from-cyan-400 to-teal-400",
    badge: "Live",
  },
  {
    href: "/compare",
    label: "Version Diff & Conflicts",
    desc: "Contradiction Engine",
    icon: CompareIcon,
    color: "from-amber-400 to-rose-500",
    badge: null,
  },
  {
    href: "/graph",
    label: "Policy Graph",
    desc: "HippoRAG & Leiden",
    icon: NetworkIcon,
    color: "from-purple-400 to-indigo-500",
    badge: "GraphRAG",
  },
  {
    href: "/okf",
    label: "OKF Ontology",
    desc: "Canonical Rules",
    icon: BookOpenIcon,
    color: "from-emerald-400 to-teal-500",
    badge: "Rules",
  },
  {
    href: "/patients",
    label: "Patient Claim Navigator",
    desc: "Personalized Eligibility",
    icon: UserIcon,
    color: "from-pink-400 to-rose-500",
    badge: null,
  },
  {
    href: "/upload",
    label: "Policy Ingestion",
    desc: "Multi-Version PDF",
    icon: UploadIcon,
    color: "from-blue-400 to-cyan-500",
    badge: null,
  },
  {
    href: "/admin",
    label: "Operations & Admin",
    desc: "Index Management",
    icon: AdminIcon,
    color: "from-slate-400 to-slate-200",
    badge: null,
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then(() => {
        if (mounted) setBackendStatus("online");
      })
      .catch(() => {
        if (mounted) setBackendStatus("offline");
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <aside className="sticky top-0 flex h-screen w-72 shrink-0 flex-col border-r border-slate-800/80 bg-slate-950/95 p-4 backdrop-blur-2xl">
      {/* Brand Header */}
      <div className="mb-6 flex items-center gap-3 px-3 py-2">
        <div className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 via-teal-500 to-indigo-600 p-0.5 shadow-glow-cyan">
          <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-slate-950">
            <ShieldCheckIcon className="h-6 w-6 text-cyan-400" />
          </div>
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-display text-lg font-black tracking-tight text-white">
              Policy<span className="text-cyan-400">Graph</span>
            </span>
            <span className="rounded bg-cyan-500/10 px-1.5 py-0.2 text-[10px] font-bold text-cyan-300 border border-cyan-500/20">
              RAG
            </span>
          </div>
          <p className="text-[11px] font-medium text-slate-400">Zero-Hallucination Engine</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 space-y-1.5 overflow-y-auto pr-1">
        <div className="px-3 pb-1 pt-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Core Workflows
        </div>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              prefetch={true}
              className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                active
                  ? "bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/30 text-white shadow-md border border-cyan-500/30"
                  : "text-slate-400 hover:bg-slate-900/60 hover:text-slate-200"
              }`}
            >
              {/* Active vertical glow indicator */}
              {active && (
                <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-cyan-400 shadow-glow-cyan" />
              )}

              {/* Icon with gradient badge */}
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-lg transition-all ${
                  active
                    ? `bg-gradient-to-tr ${item.color} text-slate-950 shadow-md font-bold`
                    : "bg-slate-900 text-slate-400 group-hover:text-cyan-400 group-hover:bg-slate-800"
                }`}
              >
                <Icon className="h-4 w-4" />
              </div>

              {/* Text metadata */}
              <div className="flex-1 truncate">
                <div className="flex items-center justify-between">
                  <span className={`truncate text-xs font-semibold ${active ? "text-white" : ""}`}>
                    {item.label}
                  </span>
                  {item.badge && (
                    <span
                      className={`ml-1 rounded px-1.5 py-0.2 text-[9px] font-semibold uppercase ${
                        active
                          ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                          : "bg-slate-800 text-slate-400 border border-slate-700"
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
                <p className="truncate text-[10px] text-slate-500">{item.desc}</p>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* System Status Footer */}
      <div className="mt-4 space-y-2 border-t border-slate-800/80 pt-3">
        {/* Guard Pill */}
        <div className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-950/40 to-teal-950/30 border border-emerald-500/20 p-2 text-[11px] text-emerald-300">
          <SparklesIcon className="h-4 w-4 text-emerald-400 shrink-0" />
          <span className="truncate">HippoRAG & Leiden Guard Active</span>
        </div>

        {/* Backend Connectivity Status */}
        <div className="flex items-center justify-between rounded-lg bg-slate-900/80 px-3 py-2 text-xs text-slate-400 border border-slate-800">
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === "online"
                  ? "bg-emerald-400 shadow-glow-emerald animate-pulse"
                  : backendStatus === "checking"
                  ? "bg-amber-400 animate-ping"
                  : "bg-rose-500"
              }`}
            />
            <span className="text-[11px] font-medium text-slate-300">
              {backendStatus === "online"
                ? "FastAPI Engine: Online"
                : backendStatus === "checking"
                ? "Checking API..."
                : "Engine: Standby"}
            </span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">v0.1.0</span>
        </div>
      </div>
    </aside>
  );
}
