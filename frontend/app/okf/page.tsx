"use client";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import { listOkfConcepts, getOkfConcept } from "@/services/api";
import type { OkfConcept } from "@/types";
import {
  BookOpenIcon,
  SparklesIcon,
  CheckCircleIcon,
  SearchIcon,
  ArrowRightIcon,
  ZapIcon,
} from "@/components/Icons";

export default function OkfPage() {
  const [concepts, setConcepts] = useState<OkfConcept[]>([]);
  const [selectedConcept, setSelectedConcept] = useState<OkfConcept | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listOkfConcepts()
      .then((data) => {
        setConcepts(data);
        if (data.length > 0) {
          getOkfConcept(data[0].id).then(setSelectedConcept).catch(() => {});
        }
      })
      .catch(() => setConcepts([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleSelect(id: string) {
    try {
      const detailed = await getOkfConcept(id);
      setSelectedConcept(detailed);
    } catch {
      // fallback
    }
  }

  const categories = ["all", ...Array.from(new Set(concepts.map((c) => c.category)))];

  const filtered = concepts.filter((c) => {
    const matchesCat = selectedCategory === "all" || c.category === selectedCategory;
    const matchesSearch =
      c.title.toLowerCase().includes(search.toLowerCase()) ||
      c.id.toLowerCase().includes(search.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
              OKF Canonical Knowledge Ontology
            </h1>
            <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-bold text-emerald-300 border border-emerald-500/30">
              Deterministic Rules
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-400">
            Open Knowledge Format (OKF) canonical concepts, regulatory insurance rules, and ontological dependencies.
          </p>
        </div>
      </div>

      {/* Search & Category Filter Bar */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <div className="relative min-w-[260px] flex-1 max-w-md">
          <SearchIcon className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search concepts by title or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-semibold capitalize transition-all ${
                selectedCategory === cat
                  ? "bg-emerald-500 text-slate-950 shadow-glow-emerald"
                  : "border border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid: Concepts List & Selected Detail */}
      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Concepts Cards List */}
        <div className="lg:col-span-1 space-y-3 max-h-[700px] overflow-y-auto pr-1">
          {loading && <p className="text-xs text-slate-400">Loading OKF concepts...</p>}
          {!loading && filtered.length === 0 && (
            <p className="text-xs text-slate-500 p-4">No matching concepts found.</p>
          )}

          {filtered.map((c) => {
            const isSelected = selectedConcept?.id === c.id;
            return (
              <div
                key={c.id}
                onClick={() => handleSelect(c.id)}
                className={`cursor-pointer rounded-2xl border p-4 backdrop-blur-xl transition-all duration-200 ${
                  isSelected
                    ? "border-emerald-500/60 bg-emerald-950/30 shadow-glow-emerald -translate-y-0.5"
                    : "border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-cyan-300">
                    {c.category}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">v{c.version}</span>
                </div>

                <h3 className="mt-2 text-sm font-bold text-white line-clamp-1">{c.title}</h3>

                <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                  <span>{c.rules_count ?? 0} Canonical Rules</span>
                  <div className="flex items-center gap-1 text-emerald-400 font-semibold">
                    <span>Inspect</span>
                    <ArrowRightIcon className="h-3 w-3" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Selected Concept Deep Dive View */}
        <Card className="lg:col-span-2 border-slate-800 bg-slate-900/70 p-6 backdrop-blur-2xl">
          {!selectedConcept && (
            <div className="flex h-96 items-center justify-center text-xs text-slate-500">
              Select an OKF concept from the list to view canonical rules and dependencies.
            </div>
          )}

          {selectedConcept && (
            <div>
              {/* Concept Title Banner */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-emerald-500/30 bg-emerald-950/60 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300">
                      {selectedConcept.category}
                    </span>
                    <span className="text-xs font-mono text-slate-500">{selectedConcept.id}</span>
                  </div>
                  <h2 className="mt-1 font-display text-xl font-bold text-white">
                    {selectedConcept.title}
                  </h2>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-1.5 text-right">
                  <div className="text-[10px] text-slate-500 uppercase font-bold">Status</div>
                  <div className="text-xs font-bold text-emerald-400 capitalize">
                    {selectedConcept.status || "active"}
                  </div>
                </div>
              </div>

              {/* Canonical Rules List */}
              <div className="mt-5">
                <h3 className="font-display text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <CheckCircleIcon className="h-4 w-4 text-emerald-400" />
                  <span>Canonical Operational Rules ({selectedConcept.rules?.length || 0})</span>
                </h3>

                <div className="mt-3 space-y-2">
                  {(!selectedConcept.rules || selectedConcept.rules.length === 0) && (
                    <p className="text-xs text-slate-500">No canonical rules registered.</p>
                  )}
                  {selectedConcept.rules?.map((rule, ri) => (
                    <div
                      key={ri}
                      className="flex items-start gap-3 rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 text-xs text-slate-200"
                    >
                      <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-emerald-500/30 text-[10px] font-bold text-emerald-300">
                        {ri + 1}
                      </span>
                      <p className="leading-relaxed">{rule}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ontological Relations */}
              {selectedConcept.relations && Object.keys(selectedConcept.relations).length > 0 && (
                <div className="mt-6 border-t border-slate-800 pt-4">
                  <h3 className="font-display text-xs font-bold uppercase tracking-wider text-slate-400">
                    Cross-Concept Relations
                  </h3>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {Object.entries(selectedConcept.relations).flatMap(([relType, items]) =>
                      (items as any[]).map((item, ii) => (
                        <div
                          key={`${relType}-${ii}`}
                          className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-1.5 text-xs text-slate-300"
                        >
                          <span className="font-mono text-cyan-400">{relType}</span> ➔{" "}
                          <span className="font-semibold text-white">{item.target || String(item)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {/* Raw Markdown Body */}
              {selectedConcept.markdown_body && (
                <div className="mt-6 border-t border-slate-800 pt-4">
                  <h3 className="font-display text-xs font-bold uppercase tracking-wider text-slate-400">
                    Full Specification Documentation
                  </h3>
                  <div className="mt-2.5 max-h-56 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/80 p-4 font-mono text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap">
                    {selectedConcept.markdown_body}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
