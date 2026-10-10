"use client";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { getPolicyGraph, listPolicies } from "@/services/api";
import type { GraphNode, GraphResponse, Policy } from "@/types";
import {
  NetworkIcon,
  SparklesIcon,
  BrainIcon,
  FilterIcon,
  ZapIcon,
  CheckCircleIcon,
} from "@/components/Icons";

const TYPE_COLORS: Record<string, { fill: string; stroke: string; glow: string; text: string }> = {
  Policy: { fill: "#00f5ff", stroke: "#22d3ee", glow: "rgba(0, 245, 255, 0.5)", text: "#a5f3fc" },
  Version: { fill: "#38bdf8", stroke: "#0ea5e9", glow: "rgba(56, 189, 248, 0.5)", text: "#bae6fd" },
  Clause: { fill: "#2dd4bf", stroke: "#14b8a6", glow: "rgba(45, 212, 191, 0.5)", text: "#99f6e4" },
  Coverage: { fill: "#10b981", stroke: "#059669", glow: "rgba(16, 185, 129, 0.5)", text: "#a7f3d0" },
  CoverageBenefit: { fill: "#34d399", stroke: "#10b981", glow: "rgba(52, 211, 153, 0.5)", text: "#a7f3d0" },
  Exclusion: { fill: "#f43f5e", stroke: "#e11d48", glow: "rgba(244, 63, 94, 0.6)", text: "#fecdd3" },
  WaitingPeriod: { fill: "#f59e0b", stroke: "#d97706", glow: "rgba(245, 158, 11, 0.5)", text: "#fde68a" },
  SubLimit: { fill: "#a855f7", stroke: "#9333ea", glow: "rgba(168, 85, 247, 0.5)", text: "#e9d5ff" },
  CoPay: { fill: "#ec4899", stroke: "#db2777", glow: "rgba(236, 72, 153, 0.5)", text: "#fbcfe8" },
  MedicalCondition: { fill: "#3b82f6", stroke: "#2563eb", glow: "rgba(59, 130, 246, 0.5)", text: "#bfdbfe" },
  Condition: { fill: "#3b82f6", stroke: "#2563eb", glow: "rgba(59, 130, 246, 0.5)", text: "#bfdbfe" },
};

function layoutNodes(graph: GraphResponse, width = 940, height = 540) {
  const byType: Record<string, GraphNode[]> = {};
  graph.nodes.forEach((n) => {
    byType[n.type] = byType[n.type] || [];
    byType[n.type].push(n);
  });
  const types = Object.keys(byType);
  const positions: Record<string, { x: number; y: number }> = {};

  types.forEach((type, ti) => {
    const nodes = byType[type];
    const colX = ((ti + 1) / (types.length + 1)) * width;
    nodes.forEach((n, ni) => {
      const y = ((ni + 1) / (nodes.length + 1)) * height;
      positions[n.id] = { x: colX, y };
    });
  });
  return positions;
}

export default function GraphPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [policyId, setPolicyId] = useState("");
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string | null>(null);

  useEffect(() => {
    listPolicies().then((p) => {
      setPolicies(p);
      if (p.length > 0) setPolicyId(p[0].id);
    }).catch(() => setPolicies([]));
  }, []);

  async function loadGraph(targetId = policyId) {
    if (!targetId) return;
    setLoading(true);
    try {
      const g = await getPolicyGraph(targetId);
      setGraph(g);
      setSelected(null);
    } finally {
      setLoading(false);
    }
  }

  // Load first graph automatically once policies are available
  useEffect(() => {
    if (policyId && !graph) {
      loadGraph(policyId);
    }
  }, [policyId]);

  const positions = graph ? layoutNodes(graph) : {};
  const allTypes = graph ? Array.from(new Set(graph.nodes.map((n) => n.type))) : [];

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
              Policy Knowledge Graph & GraphRAG
            </h1>
            <span className="rounded-full bg-purple-500/10 px-2.5 py-0.5 text-xs font-bold text-purple-300 border border-purple-500/30">
              Leiden Partitions
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-400">
            HippoRAG associative memory graph traversal & Microsoft GraphRAG hierarchical community clusters.
          </p>
        </div>

        {/* Policy Selector & Reload */}
        <div className="flex items-center gap-2.5">
          <select
            className="rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
            value={policyId}
            onChange={(e) => {
              setPolicyId(e.target.value);
              loadGraph(e.target.value);
            }}
          >
            <option value="">Select a policy…</option>
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.insurer})
              </option>
            ))}
          </select>

          <button
            onClick={() => loadGraph()}
            disabled={!policyId || loading}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-500 px-4 py-2 text-xs font-bold text-white shadow-glow-purple transition-all duration-200 hover:scale-105 disabled:opacity-40"
          >
            {loading ? "Traversing..." : "Reload Graph"}
          </button>
        </div>
      </div>

      {/* Filter Chips Strip */}
      {graph && (
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Filter Nodes:
          </span>
          <button
            onClick={() => setFilterType(null)}
            className={`rounded-full px-2.5 py-1 text-[11px] font-bold transition-all ${
              filterType === null
                ? "bg-cyan-500 text-slate-950 shadow-glow-cyan"
                : "border border-slate-800 bg-slate-900 text-slate-400 hover:text-white"
            }`}
          >
            All Entities ({graph.nodes.length})
          </button>
          {allTypes.map((t) => {
            const conf = TYPE_COLORS[t] || { fill: "#94a3b8", glow: "transparent" };
            const isActive = filterType === t;
            return (
              <button
                key={t}
                onClick={() => setFilterType(isActive ? null : t)}
                className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-bold transition-all ${
                  isActive
                    ? "border border-white/40 text-white shadow-lg"
                    : "border border-slate-800/80 bg-slate-900/60 text-slate-300 hover:border-slate-700"
                }`}
                style={{ backgroundColor: isActive ? conf.fill : undefined }}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: conf.fill, boxShadow: `0 0 6px ${conf.glow}` }}
                />
                <span>{t}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Main Content Grid */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* SVG Graph Viewport */}
        <Card className="lg:col-span-2 overflow-hidden border-slate-800 bg-slate-950/80 p-0 shadow-2xl backdrop-blur-2xl">
          <div className="flex items-center justify-between border-b border-slate-800/80 px-4 py-3 bg-slate-900/50">
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-cyan-400 shadow-glow-cyan animate-pulse" />
              <span className="text-xs font-bold text-white">Associative Knowledge Network</span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono">
              {graph ? `${graph.nodes.length} nodes · ${graph.edges.length} relations` : "0 nodes"}
            </div>
          </div>

          <div className="relative overflow-auto p-2" style={{ minHeight: "540px" }}>
            {!graph && (
              <div className="flex h-96 items-center justify-center text-xs text-slate-500">
                Select a policy to render its HippoRAG knowledge graph
              </div>
            )}

            {graph && (
              <svg width={940} height={540} className="select-none mx-auto">
                <defs>
                  {/* Subtle Grid Pattern */}
                  <pattern id="graphGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#graphGrid)" />

                {/* Edges */}
                {graph.edges.map((e, i) => {
                  const s = positions[e.source];
                  const t = positions[e.target];
                  if (!s || !t) return null;
                  const isContradiction = e.relation === "CONTRADICTS";
                  return (
                    <line
                      key={i}
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke={isContradiction ? "#f43f5e" : "#334155"}
                      strokeWidth={isContradiction ? 2 : 1}
                      strokeDasharray={isContradiction ? "5,4" : undefined}
                      opacity={isContradiction ? 0.9 : 0.4}
                    />
                  );
                })}

                {/* Nodes */}
                {graph.nodes.map((n) => {
                  const p = positions[n.id];
                  if (!p) return null;
                  const isSelected = selected?.id === n.id;
                  const isDimmed = filterType && filterType !== n.type;
                  const conf = TYPE_COLORS[n.type] || { fill: "#94a3b8", stroke: "#cbd5e1", glow: "transparent" };

                  return (
                    <g
                      key={n.id}
                      onClick={() => setSelected(n)}
                      className="cursor-pointer transition-transform hover:scale-110"
                      opacity={isDimmed ? 0.2 : 1}
                    >
                      {/* Aura halo for selected */}
                      {isSelected && (
                        <circle
                          cx={p.x}
                          cy={p.y}
                          r={20}
                          fill="none"
                          stroke={conf.fill}
                          strokeWidth={2}
                          strokeDasharray="3,3"
                          className="animate-spin"
                        />
                      )}

                      {/* Main Node circle */}
                      <circle
                        cx={p.x}
                        cy={p.y}
                        r={isSelected ? 13 : 9}
                        fill={conf.fill}
                        stroke={isSelected ? "#ffffff" : conf.stroke}
                        strokeWidth={isSelected ? 3 : 1.5}
                        style={{ filter: `drop-shadow(0 0 6px ${conf.glow})` }}
                      />

                      {/* Label Text */}
                      <text
                        x={p.x + 14}
                        y={p.y + 4}
                        fontSize={10}
                        fill={isSelected ? "#ffffff" : "#cbd5e1"}
                        fontWeight={isSelected ? "bold" : "500"}
                      >
                        {n.label.slice(0, 26)}
                      </text>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        </Card>

        {/* Right Sidebar: Node Inspector & Communities */}
        <div className="space-y-5">
          {/* Node Inspector */}
          <Card className="border-slate-800 bg-slate-900/70 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-display text-sm font-bold text-white flex items-center gap-1.5">
                <BrainIcon className="h-4 w-4 text-cyan-400" />
                <span>Entity Node Inspector</span>
              </h3>
              {selected && (
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400 font-mono">
                  {selected.id.slice(0, 8)}...
                </span>
              )}
            </div>

            {!selected && (
              <div className="p-6 text-center text-xs text-slate-500">
                Click any graph node to inspect its attributes, policy sections, and relations.
              </div>
            )}

            {selected && (
              <div className="mt-3 space-y-3 text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className="h-3 w-3 rounded-full"
                    style={{ backgroundColor: TYPE_COLORS[selected.type]?.fill || "#94a3b8" }}
                  />
                  <span className="font-bold text-white">{selected.type}</span>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 font-semibold text-slate-200">
                  {selected.label}
                </div>

                {selected.data && Object.keys(selected.data).length > 0 && (
                  <div className="space-y-1.5 rounded-xl border border-slate-800/80 bg-slate-950/50 p-3">
                    {Object.entries(selected.data).map(([k, v]) => (
                      <div key={k} className="flex justify-between text-slate-400">
                        <span className="font-medium text-slate-500">{k}:</span>
                        <span className="text-right truncate max-w-[160px] text-slate-200 font-mono">
                          {String(v)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* GraphRAG Communities Panel */}
          {graph && graph.communities && graph.communities.length > 0 && (
            <Card className="border-slate-800 bg-slate-900/70 p-5 backdrop-blur-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="font-display text-sm font-bold text-white flex items-center gap-1.5">
                  <NetworkIcon className="h-4 w-4 text-purple-400" />
                  <span>GraphRAG Communities</span>
                </h3>
                <span className="rounded-full border border-purple-500/30 bg-purple-950/60 px-2 py-0.5 text-[10px] font-bold text-purple-300">
                  {graph.communities.length} clusters
                </span>
              </div>
              <p className="mt-2 text-[11px] text-slate-400">Leiden community partitions & summary abstracts</p>

              <div className="mt-3 space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {graph.communities.map((comm: any, idx: number) => (
                  <div
                    key={idx}
                    className="rounded-xl border border-purple-500/20 bg-purple-950/20 p-3 text-xs transition-all hover:border-purple-500/40"
                  >
                    <div className="flex items-center justify-between font-bold text-purple-200">
                      <span>{comm.theme || `Community ${comm.community_id ?? idx + 1}`}</span>
                      <span className="text-[10px] text-purple-400 font-normal">
                        {comm.node_count ?? "?"} nodes
                      </span>
                    </div>

                    {comm.summary && (
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-300 line-clamp-3 hover:line-clamp-none">
                        {comm.summary}
                      </p>
                    )}

                    {comm.key_entities && comm.key_entities.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {comm.key_entities.slice(0, 4).map((ent: string, ei: number) => (
                          <span
                            key={ei}
                            className="rounded bg-slate-900/90 px-1.5 py-0.5 text-[9px] font-medium text-slate-300 border border-slate-800"
                          >
                            {ent}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
