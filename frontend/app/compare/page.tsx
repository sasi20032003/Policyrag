"use client";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { comparePolicyVersions, listPolicies } from "@/services/api";
import type { ClauseDiff, CompareResponse, Policy } from "@/types";
import {
  CompareIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  SparklesIcon,
  ArrowRightIcon,
  ZapIcon,
} from "@/components/Icons";

const TYPE_CONFIG: Record<
  string,
  { label: string; badge: string; border: string; bg: string; text: string }
> = {
  CONTRADICTORY: {
    label: "Contradiction / Conflict",
    badge: "border-red-500/50 bg-red-950/70 text-red-300 shadow-glow-rose",
    border: "border-l-4 border-l-red-500 border-slate-800",
    bg: "bg-red-950/20",
    text: "text-red-300",
  },
  UPDATED: {
    label: "Clause Modified",
    badge: "border-amber-500/50 bg-amber-950/70 text-amber-300",
    border: "border-l-4 border-l-amber-500 border-slate-800",
    bg: "bg-amber-950/20",
    text: "text-amber-300",
  },
  ADDED: {
    label: "New Clause Added",
    badge: "border-emerald-500/50 bg-emerald-950/70 text-emerald-300 shadow-glow-emerald",
    border: "border-l-4 border-l-emerald-500 border-slate-800",
    bg: "bg-emerald-950/20",
    text: "text-emerald-300",
  },
  REMOVED: {
    label: "Clause Removed",
    badge: "border-rose-500/50 bg-rose-950/70 text-rose-300",
    border: "border-l-4 border-l-rose-500 border-slate-800",
    bg: "bg-rose-950/20",
    text: "text-rose-300",
  },
  SAME: {
    label: "Unchanged",
    badge: "border-slate-700 bg-slate-800 text-slate-300",
    border: "border-slate-800",
    bg: "bg-slate-900/40",
    text: "text-slate-400",
  },
};

function DiffCard({ item }: { item: ClauseDiff }) {
  const conf = TYPE_CONFIG[item.type] || TYPE_CONFIG.SAME;
  return (
    <div
      className={`rounded-2xl border p-4 backdrop-blur-xl transition-all duration-200 hover:border-slate-700 ${conf.border} ${conf.bg}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider ${conf.badge}`}>
          {conf.label}
        </span>
        {item.confidence > 0 && (
          <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700">
            NLI Confidence: {Math.round(item.confidence * 100)}%
          </span>
        )}
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
        {item.clause_a && (
          <div className="rounded-xl border border-rose-500/20 bg-slate-950/70 p-3 text-xs">
            <div className="mb-1 font-bold text-rose-400 flex items-center gap-1">
              <span>Old Version (A)</span>
            </div>
            <p className="text-slate-300 leading-relaxed">{item.clause_a}</p>
          </div>
        )}
        {item.clause_b && (
          <div className="rounded-xl border border-emerald-500/20 bg-slate-950/70 p-3 text-xs">
            <div className="mb-1 font-bold text-emerald-400 flex items-center gap-1">
              <span>New Version (B)</span>
            </div>
            <p className="text-slate-300 leading-relaxed">{item.clause_b}</p>
          </div>
        )}
      </div>

      {item.explanation && (
        <div className="mt-3 rounded-xl border border-slate-800/80 bg-slate-950/50 p-2.5 text-xs text-slate-400">
          <span className="font-semibold text-cyan-300">Semantic Impact: </span>
          {item.explanation}
        </div>
      )}
    </div>
  );
}

export default function ComparePage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [versionA, setVersionA] = useState("");
  const [versionB, setVersionB] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"all" | "contradictions" | "modified" | "added" | "removed">("all");

  useEffect(() => {
    listPolicies().then(setPolicies).catch(() => setPolicies([]));
  }, []);

  const allVersions = policies.flatMap((p) =>
    p.versions.map((v) => ({ id: v.id, label: `${p.name} — ${v.version}` }))
  );

  async function handleCompare() {
    if (!versionA || !versionB) return;
    setLoading(true);
    setError(null);
    try {
      const res = await comparePolicyVersions(versionA, versionB);
      setResult(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Comparison failed. Backend might be down.");
    } finally {
      setLoading(false);
    }
  }

  const contradictionsCount = result?.contradictions.length || 0;
  const modifiedCount = result?.modified.length || 0;
  const addedCount = result?.added.length || 0;
  const removedCount = result?.removed.length || 0;
  const totalDiffs = contradictionsCount + modifiedCount + addedCount + removedCount;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 lg:px-10">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
              Policy Version Diff & Contradictions
            </h1>
            <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-bold text-amber-300 border border-amber-500/30">
              NLI Engine
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-400">
            Compare two contract versions to flag coverage reductions, added co-pays, and conflicting terms.
          </p>
        </div>
      </div>

      {/* Version Selector Card */}
      <Card className="mt-6 border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
              Version A (Older / Base Policy)
            </label>
            <select
              className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
              value={versionA}
              onChange={(e) => setVersionA(e.target.value)}
            >
              <option value="">Select older version…</option>
              {allVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
              Version B (Newer / Renewal Policy)
            </label>
            <select
              className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2.5 text-sm text-white focus:border-cyan-500 focus:outline-none"
              value={versionB}
              onChange={(e) => setVersionB(e.target.value)}
            >
              <option value="">Select newer version…</option>
              {allVersions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          onClick={handleCompare}
          disabled={loading || !versionA || !versionB}
          className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-rose-500 px-5 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-orange-950/40 transition-all duration-200 hover:scale-[1.01] hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <span className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
              <span>Analyzing Semantic Diffs with NLI...</span>
            </>
          ) : (
            <>
              <CompareIcon className="h-4 w-4 text-slate-950" />
              <span>Compare Policy Versions</span>
            </>
          )}
        </button>

        {error && (
          <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
            {error}
          </div>
        )}
      </Card>

      {/* Results Section */}
      {result && (
        <div className="mt-8 space-y-6">
          {/* Summary Metric Counters */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div
              onClick={() => setActiveTab("contradictions")}
              className={`cursor-pointer rounded-2xl border p-4 backdrop-blur-xl transition-all ${
                activeTab === "contradictions"
                  ? "border-red-500/60 bg-red-950/40 shadow-glow-rose"
                  : "border-slate-800 bg-slate-900/60 hover:border-red-500/40"
              }`}
            >
              <div className="flex items-center justify-between text-xs text-red-400 font-bold">
                <span>Contradictions</span>
                <AlertTriangleIcon className="h-4 w-4" />
              </div>
              <div className="mt-2 font-display text-3xl font-black text-red-300">
                {contradictionsCount}
              </div>
            </div>

            <div
              onClick={() => setActiveTab("modified")}
              className={`cursor-pointer rounded-2xl border p-4 backdrop-blur-xl transition-all ${
                activeTab === "modified"
                  ? "border-amber-500/60 bg-amber-950/40"
                  : "border-slate-800 bg-slate-900/60 hover:border-amber-500/40"
              }`}
            >
              <div className="flex items-center justify-between text-xs text-amber-400 font-bold">
                <span>Modified</span>
                <ZapIcon className="h-4 w-4" />
              </div>
              <div className="mt-2 font-display text-3xl font-black text-amber-300">
                {modifiedCount}
              </div>
            </div>

            <div
              onClick={() => setActiveTab("added")}
              className={`cursor-pointer rounded-2xl border p-4 backdrop-blur-xl transition-all ${
                activeTab === "added"
                  ? "border-emerald-500/60 bg-emerald-950/40 shadow-glow-emerald"
                  : "border-slate-800 bg-slate-900/60 hover:border-emerald-500/40"
              }`}
            >
              <div className="flex items-center justify-between text-xs text-emerald-400 font-bold">
                <span>Added</span>
                <CheckCircleIcon className="h-4 w-4" />
              </div>
              <div className="mt-2 font-display text-3xl font-black text-emerald-300">
                {addedCount}
              </div>
            </div>

            <div
              onClick={() => setActiveTab("removed")}
              className={`cursor-pointer rounded-2xl border p-4 backdrop-blur-xl transition-all ${
                activeTab === "removed"
                  ? "border-rose-500/60 bg-rose-950/40"
                  : "border-slate-800 bg-slate-900/60 hover:border-rose-500/40"
              }`}
            >
              <div className="flex items-center justify-between text-xs text-rose-400 font-bold">
                <span>Removed</span>
                <span className="text-sm font-bold">✕</span>
              </div>
              <div className="mt-2 font-display text-3xl font-black text-rose-300">
                {removedCount}
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto border-b border-slate-800/80 pb-2">
            {[
              { id: "all", label: `All Changes (${totalDiffs})` },
              { id: "contradictions", label: `Contradictions (${contradictionsCount})` },
              { id: "modified", label: `Modified (${modifiedCount})` },
              { id: "added", label: `Added (${addedCount})` },
              { id: "removed", label: `Removed (${removedCount})` },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`rounded-xl px-3.5 py-1.5 text-xs font-bold transition-all ${
                  activeTab === tab.id
                    ? "bg-slate-800 text-cyan-300 border border-cyan-500/40 shadow-sm"
                    : "text-slate-400 hover:text-white hover:bg-slate-900"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Diff Cards Feed */}
          <div className="space-y-3">
            {totalDiffs === 0 && (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-center text-slate-400">
                No differences detected between selected versions.
              </div>
            )}

            {(activeTab === "all" || activeTab === "contradictions") &&
              result.contradictions.map((item, idx) => <DiffCard key={`c-${idx}`} item={item} />)}

            {(activeTab === "all" || activeTab === "modified") &&
              result.modified.map((item, idx) => <DiffCard key={`m-${idx}`} item={item} />)}

            {(activeTab === "all" || activeTab === "added") &&
              result.added.map((item, idx) => <DiffCard key={`a-${idx}`} item={item} />)}

            {(activeTab === "all" || activeTab === "removed") &&
              result.removed.map((item, idx) => <DiffCard key={`r-${idx}`} item={item} />)}
          </div>
        </div>
      )}
    </div>
  );
}
