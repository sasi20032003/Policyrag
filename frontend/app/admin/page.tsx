"use client";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { deletePolicy, listPolicies, reprocessPolicy } from "@/services/api";
import type { Policy } from "@/types";
import {
  AdminIcon,
  RefreshCwIcon,
  TrashIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  FileTextIcon,
  LayersIcon,
} from "@/components/Icons";

const STATUS_STYLES: Record<string, { badge: string; dot: string }> = {
  ready: {
    badge: "border-emerald-500/40 bg-emerald-950/60 text-emerald-300 shadow-glow-emerald",
    dot: "bg-emerald-400",
  },
  processing: {
    badge: "border-amber-500/40 bg-amber-950/60 text-amber-300",
    dot: "bg-amber-400 animate-ping",
  },
  pending: {
    badge: "border-slate-700 bg-slate-800 text-slate-300",
    dot: "bg-slate-400",
  },
  failed: {
    badge: "border-rose-500/40 bg-rose-950/60 text-rose-300 shadow-glow-rose",
    dot: "bg-rose-400",
  },
};

export default function AdminPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setPolicies(await listPolicies());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleReprocess(policyId: string) {
    setActionLoading(`reprocess-${policyId}`);
    try {
      await reprocessPolicy(policyId);
      await refresh();
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDelete(policyId: string) {
    if (!confirm("Permanently delete this policy, its versions, and its knowledge graph chunks?")) return;
    setActionLoading(`delete-${policyId}`);
    try {
      await deletePolicy(policyId);
      await refresh();
    } finally {
      setActionLoading(null);
    }
  }

  const totalVersions = policies.reduce((acc, p) => acc + p.versions.length, 0);
  const totalChunks = policies.reduce(
    (acc, p) => acc + p.versions.reduce((vAcc, v) => vAcc + (v.chunk_count || 0), 0),
    0
  );

  return (
    <div className="mx-auto max-w-6xl px-6 py-10 lg:px-10">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
              Operations & Policy Management
            </h1>
            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-mono text-cyan-300 border border-slate-700">
              Admin Ops
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-400">
            Monitor ingested policies, inspect chunk counts, reprocess embeddings, and manage version lifecycles.
          </p>
        </div>

        <button
          onClick={refresh}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/80 px-4 py-2 text-xs font-bold text-slate-200 hover:border-cyan-500 hover:text-white transition-all disabled:opacity-40"
        >
          <RefreshCwIcon className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh List</span>
        </button>
      </div>

      {/* Operational Stats Strip */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-xl">
          <div className="text-[11px] font-bold uppercase text-slate-400">Total Policies</div>
          <div className="mt-1 font-display text-3xl font-black text-cyan-400">{policies.length}</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-xl">
          <div className="text-[11px] font-bold uppercase text-slate-400">Policy Versions</div>
          <div className="mt-1 font-display text-3xl font-black text-purple-400">{totalVersions}</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-xl">
          <div className="text-[11px] font-bold uppercase text-slate-400">Indexed Chunks</div>
          <div className="mt-1 font-display text-3xl font-black text-emerald-400">{totalChunks}</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-xl">
          <div className="text-[11px] font-bold uppercase text-slate-400">Index Status</div>
          <div className="mt-1 flex items-center gap-2 text-sm font-bold text-emerald-400">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-glow-emerald animate-pulse" />
            <span>Healthy</span>
          </div>
        </div>
      </div>

      {/* Policies Feed */}
      <div className="mt-8 space-y-4">
        {loading && <p className="text-xs text-slate-400">Refreshing policy repository...</p>}
        {!loading && policies.length === 0 && (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-10 text-center text-xs text-slate-500">
            No policies uploaded yet. Use the Policy Ingestion page to upload your first document.
          </div>
        )}

        {policies.map((policy) => (
          <Card key={policy.id} className="border-slate-800 bg-slate-900/70 p-5 backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-display text-base font-bold text-white">{policy.name}</span>
                  <span className="rounded-md bg-slate-800 px-2 py-0.5 text-[10px] font-semibold text-cyan-300 border border-slate-700">
                    {policy.insurer}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-500">ID: {policy.id}</div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleReprocess(policy.id)}
                  disabled={actionLoading === `reprocess-${policy.id}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/40 bg-cyan-950/40 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/50 transition-all disabled:opacity-40"
                >
                  <RefreshCwIcon className="h-3 w-3" />
                  <span>Reprocess</span>
                </button>
                <button
                  onClick={() => handleDelete(policy.id)}
                  disabled={actionLoading === `delete-${policy.id}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/40 bg-rose-950/40 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-900/50 transition-all disabled:opacity-40"
                >
                  <TrashIcon className="h-3 w-3" />
                  <span>Delete</span>
                </button>
              </div>
            </div>

            {/* Versions Table */}
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-[10px] uppercase font-bold text-slate-500 border-b border-slate-800/80">
                    <th className="py-2">Version</th>
                    <th>Effective Timeline</th>
                    <th>Status</th>
                    <th>Dense Chunks</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {policy.versions.map((v) => {
                    const statusConfig = STATUS_STYLES[v.status] || STATUS_STYLES.pending;
                    return (
                      <tr key={v.id} className="text-slate-300">
                        <td className="py-2.5 font-mono font-bold text-white">{v.version}</td>
                        <td className="font-mono text-[11px] text-slate-400">
                          {v.effective_from} ➔ {v.effective_until ?? "Open (Current)"}
                        </td>
                        <td>
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${statusConfig.badge}`}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full ${statusConfig.dot}`} />
                            <span>{v.status}</span>
                          </span>
                        </td>
                        <td className="font-mono text-cyan-300">{v.chunk_count}</td>
                        <td className="text-[11px] text-slate-500">
                          {new Date(v.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
