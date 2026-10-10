"use client";
import { useState } from "react";
import Card from "@/components/Card";
import { uploadPolicy } from "@/services/api";
import {
  UploadIcon,
  SparklesIcon,
  FileTextIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  ZapIcon,
} from "@/components/Icons";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [policyName, setPolicyName] = useState("");
  const [insurer, setInsurer] = useState("");
  const [version, setVersion] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveUntil, setEffectiveUntil] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleAutoFill(name: string, ins: string, ver: string, fromDate: string) {
    setPolicyName(name);
    setInsurer(ins);
    setVersion(ver);
    setEffectiveFrom(fromDate);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Please choose a policy PDF document.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setStatus(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("policy_name", policyName);
      form.append("insurer", insurer);
      form.append("version", version);
      form.append("effective_from", effectiveFrom);
      if (effectiveUntil) form.append("effective_until", effectiveUntil);

      const result = await uploadPolicy(form);
      setStatus(`Policy upload accepted (${result.status || "queued"}). Dense X embedding & HippoRAG graph construction are executing in the background.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Upload failed. Verify backend is running on port 8000.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-10 lg:px-10">
      {/* Header */}
      <div className="border-b border-slate-800/80 pb-5">
        <div className="flex items-center gap-2">
          <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
            Policy Document Ingestion Portal
          </h1>
          <span className="rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-bold text-blue-300 border border-blue-500/30">
            Multi-Version
          </span>
        </div>
        <p className="mt-1 text-xs sm:text-sm text-slate-400">
          Upload insurance policy PDF schedules to automatically trigger Dense X chunking, HippoRAG graph compilation, and Leiden community partitioning.
        </p>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Form */}
        <Card className="lg:col-span-2 border-slate-800 bg-slate-900/70 p-6 backdrop-blur-xl">
          {/* Quick Preset Buttons */}
          <div className="mb-5 flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-bold uppercase text-slate-500">Quick Fill Metadata:</span>
            <button
              type="button"
              onClick={() => handleAutoFill("Star Health Premier Shield", "Star Health", "v2.0", "2024-01-01")}
              className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-500 hover:text-white"
            >
              Star Health 2024
            </button>
            <button
              type="button"
              onClick={() => handleAutoFill("Care Supreme Health Floater", "Care Health", "v1.2", "2023-06-01")}
              className="rounded-lg border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-500 hover:text-white"
            >
              Care Health 2023
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* PDF File Dropzone */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                Policy Document (PDF)
              </label>
              <div className="mt-1.5 flex justify-center rounded-2xl border-2 border-dashed border-slate-700 bg-slate-950/60 px-6 py-8 hover:border-cyan-500/60 transition-all">
                <div className="text-center">
                  <UploadIcon className="mx-auto h-10 w-10 text-cyan-400" />
                  <div className="mt-2 text-xs text-slate-300">
                    <label className="cursor-pointer font-bold text-cyan-400 hover:text-cyan-300">
                      <span>Click to select PDF</span>
                      <input
                        type="file"
                        accept="application/pdf"
                        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                        className="sr-only"
                        required
                      />
                    </label>
                    <span className="text-slate-500"> or drag and drop</span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-500">Supported format: PDF up to 50MB</p>

                  {file && (
                    <div className="mt-3 inline-flex items-center gap-2 rounded-xl bg-cyan-950/80 px-3 py-1.5 text-xs font-bold text-cyan-300 border border-cyan-500/40">
                      <FileTextIcon className="h-4 w-4" />
                      <span>{file.name}</span>
                      <span className="text-[10px] text-cyan-400 font-mono">
                        ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Policy Name
                </label>
                <input
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  placeholder="e.g. Optima Secure Individual"
                  value={policyName}
                  onChange={(e) => setPolicyName(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Insurance Provider
                </label>
                <input
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  placeholder="e.g. HDFC ERGO / Star Health"
                  value={insurer}
                  onChange={(e) => setInsurer(e.target.value)}
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                Policy Version Identifier
              </label>
              <input
                className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2.5 text-xs text-white focus:border-cyan-500 focus:outline-none"
                placeholder="e.g. v2024-01, v2.0, Schedule-B"
                value={version}
                onChange={(e) => setVersion(e.target.value)}
                required
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Effective From (Valid Date)
                </label>
                <input
                  type="date"
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
                  Effective Until (Optional)
                </label>
                <input
                  type="date"
                  className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-950/90 px-3.5 py-2 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  value={effectiveUntil}
                  onChange={(e) => setEffectiveUntil(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 px-5 py-3 text-sm font-bold text-slate-950 shadow-glow-cyan hover:from-cyan-400 hover:to-teal-400 transition-all disabled:opacity-40"
            >
              {submitting ? (
                <>
                  <span className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                  <span>Processing Policy & Compiling Graph...</span>
                </>
              ) : (
                <>
                  <UploadIcon className="h-4 w-4" />
                  <span>Ingest & Index Policy</span>
                </>
              )}
            </button>

            {status && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-3 text-xs text-emerald-300">
                <div className="flex items-center gap-1.5 font-bold">
                  <CheckCircleIcon className="h-4 w-4 text-emerald-400" />
                  <span>Ingestion Successful</span>
                </div>
                <p className="mt-1 text-slate-300">{status}</p>
              </div>
            )}

            {error && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-950/40 p-3 text-xs text-rose-300">
                <div className="flex items-center gap-1.5 font-bold">
                  <AlertTriangleIcon className="h-4 w-4 text-rose-400" />
                  <span>Error</span>
                </div>
                <p className="mt-1">{error}</p>
              </div>
            )}
          </form>
        </Card>

        {/* Pipeline Info Guide */}
        <div className="space-y-4">
          <Card className="border-slate-800 bg-slate-900/70 p-5 backdrop-blur-xl">
            <h3 className="font-display text-sm font-bold text-white flex items-center gap-2">
              <ZapIcon className="h-4 w-4 text-amber-400" />
              <span>Automated Indexing Pipeline</span>
            </h3>

            <div className="mt-4 space-y-3">
              {[
                { title: "1. Layout-Aware PDF Parser", desc: "Extracts sections, clause tables, exclusions, and waiting periods with page tags." },
                { title: "2. Dense X Proposition Chunking", desc: "Segments complex policy paragraphs into atomic factual propositions." },
                { title: "3. HippoRAG Knowledge Graph", desc: "Identifies entities, co-pays, sub-limits, and creates bidirectional semantic edges." },
                { title: "4. Leiden Community Partitioning", desc: "Hierarchically groups related clauses for macro-level coverage summaries." },
              ].map((step, idx) => (
                <div key={idx} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs">
                  <div className="font-bold text-cyan-300">{step.title}</div>
                  <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">{step.desc}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
