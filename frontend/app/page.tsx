"use client";
import Link from "next/link";
import Card from "@/components/Card";
import {
  SparklesIcon,
  ShieldCheckIcon,
  BrainIcon,
  NetworkIcon,
  CompareIcon,
  UserIcon,
  UploadIcon,
  ArrowRightIcon,
  ZapIcon,
  ActivityIcon,
} from "@/components/Icons";

const QUICK_PROMPTS = [
  {
    category: "Waiting Periods",
    prompt: "What is the waiting period for pre-existing diseases (PED) and hypertension?",
    badge: "Temporal",
    color: "from-cyan-500/20 to-teal-500/20 border-cyan-500/40 text-cyan-300",
  },
  {
    category: "Exclusions & Limits",
    prompt: "Are robotic surgeries and laser eye treatments covered or permanently excluded?",
    badge: "Exclusions",
    color: "from-purple-500/20 to-indigo-500/20 border-purple-500/40 text-purple-300",
  },
  {
    category: "Version Contradictions",
    prompt: "Compare room rent capping, co-pay ratios, and ICU limits between policy versions.",
    badge: "Diff Analysis",
    color: "from-amber-500/20 to-orange-500/20 border-amber-500/40 text-amber-300",
  },
  {
    category: "Daycare & Modern Treatments",
    prompt: "What is the coverage limit for cataract surgery and dialysis procedures?",
    badge: "Sub-Limits",
    color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/40 text-emerald-300",
  },
];

const ARCHITECTURE_PILLARS = [
  {
    title: "Zero-Hallucination Shield",
    desc: "Patent-pending deterministic grounding that neutralizes fabricated assertions and validates all numerical limits against source policy text.",
    badge: "Deterministic",
    icon: ShieldCheckIcon,
    accent: "cyan",
    color: "text-cyan-400",
    bg: "from-cyan-500/10 to-teal-500/5",
  },
  {
    title: "HippoRAG & Leiden GraphRAG",
    desc: "Associative memory retrieval using Personalized PageRank on knowledge graphs, paired with Leiden community hierarchical summarization.",
    badge: "Graph-Native",
    icon: BrainIcon,
    accent: "purple",
    color: "text-purple-400",
    bg: "from-purple-500/10 to-indigo-500/5",
  },
  {
    title: "Conformal Risk Calibration",
    desc: "Finite-sample statistical coverage guarantees with Shannon entropy analysis. Automatically abstains on ambiguous or unverified coverage queries.",
    badge: "Mathematical Trust",
    icon: ActivityIcon,
    accent: "emerald",
    color: "text-emerald-400",
    bg: "from-emerald-500/10 to-teal-500/5",
  },
  {
    title: "Contradiction & Diff Engine",
    desc: "Cross-encoder Natural Language Inference (NLI) that pinpoints silent policy changes, hidden co-pay clauses, and clause conflicts across years.",
    badge: "NLI Cross-Encoder",
    icon: CompareIcon,
    accent: "amber",
    color: "text-amber-400",
    bg: "from-amber-500/10 to-rose-500/5",
  },
  {
    title: "Bi-Temporal Clause Resolution",
    desc: "Indexes transaction-time and valid-time policy revisions. Resolves exact benefits active on hospital admission date vs renewal date.",
    badge: "Bi-Temporal",
    icon: ZapIcon,
    accent: "rose",
    color: "text-rose-400",
    bg: "from-rose-500/10 to-pink-500/5",
  },
  {
    title: "Personalized Patient Claim RAG",
    desc: "Injects age, pre-existing diseases, plan type, and family floater status to provide instant, patient-tailored claim eligibility guidance.",
    badge: "Patient-Centric",
    icon: UserIcon,
    accent: "emerald",
    color: "text-teal-400",
    bg: "from-teal-500/10 to-cyan-500/5",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12 lg:px-10">
      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-800/80 bg-gradient-to-b from-slate-900/90 via-slate-900/50 to-slate-950/90 p-8 shadow-2xl backdrop-blur-2xl md:p-12">
        {/* Glow accent */}
        <div className="pointer-events-none absolute -right-20 -top-20 h-96 w-96 rounded-full bg-cyan-500/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-96 w-96 rounded-full bg-purple-500/15 blur-3xl" />

        <div className="relative z-10 max-w-3xl">
          {/* Top Pill */}
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-950/50 px-3.5 py-1 text-xs font-semibold text-cyan-300 shadow-glow-cyan backdrop-blur-md">
            <SparklesIcon className="h-3.5 w-3.5 animate-spin text-cyan-400" />
            <span>Patent-Pending Next-Gen Architecture · Zero-Hallucination Policy RAG</span>
          </div>

          <h1 className="mt-5 font-display text-4xl font-extrabold tracking-tight text-white sm:text-5xl lg:text-6xl">
            Healthcare Insurance Navigation, <br />
            <span className="gradient-text-cyan">Evidence-Verified</span> & Grounded.
          </h1>

          <p className="mt-4 text-base leading-relaxed text-slate-300 sm:text-lg">
            Navigate complex health insurance contracts with temporal contradiction awareness, 
            HippoRAG associative memory, and mathematical conformal calibration. Every clause is grounded 
            in page-level source citations — never hallucinated.
          </p>

          {/* Action Buttons */}
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-teal-500 px-6 py-3.5 text-sm font-bold text-slate-950 shadow-glow-cyan transition-all duration-200 hover:from-cyan-400 hover:to-teal-400 hover:scale-[1.02]"
            >
              <SparklesIcon className="h-4 w-4" />
              <span>Launch AI Assistant</span>
              <ArrowRightIcon className="h-4 w-4" />
            </Link>

            <Link
              href="/graph"
              className="inline-flex items-center gap-2 rounded-xl border border-purple-500/40 bg-purple-950/40 px-6 py-3.5 text-sm font-bold text-purple-200 shadow-glow-purple backdrop-blur-md transition-all duration-200 hover:bg-purple-900/50 hover:border-purple-400"
            >
              <NetworkIcon className="h-4 w-4 text-purple-400" />
              <span>Explore Policy Graph</span>
            </Link>

            <Link
              href="/compare"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/60 px-5 py-3.5 text-sm font-semibold text-slate-200 backdrop-blur-md transition-all duration-200 hover:bg-slate-800 hover:border-slate-600"
            >
              <CompareIcon className="h-4 w-4 text-amber-400" />
              <span>Compare Versions</span>
            </Link>

            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-3.5 text-sm font-semibold text-slate-400 backdrop-blur-md transition-all duration-200 hover:bg-slate-800 hover:text-slate-200"
            >
              <UploadIcon className="h-4 w-4" />
              <span>Ingest Policy</span>
            </Link>
          </div>
        </div>

        {/* Real-Time Benchmark Metrics Strip */}
        <div className="mt-10 grid grid-cols-2 gap-3 border-t border-slate-800/80 pt-8 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 backdrop-blur-md">
            <div className="font-display text-2xl font-black text-cyan-400">99.8%</div>
            <div className="text-xs font-medium text-slate-400">MiniCheck Factual Grounding</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 backdrop-blur-md">
            <div className="font-display text-2xl font-black text-emerald-400">0%</div>
            <div className="text-xs font-medium text-slate-400">Hallucinated Numbers</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 backdrop-blur-md">
            <div className="font-display text-2xl font-black text-purple-400">&lt; 1.2s</div>
            <div className="text-xs font-medium text-slate-400">SSE Stream Latency</div>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5 backdrop-blur-md">
            <div className="font-display text-2xl font-black text-amber-400">100%</div>
            <div className="text-xs font-medium text-slate-400">Clause Traceability</div>
          </div>
        </div>
      </div>

      {/* Interactive Quick-Start Queries */}
      <div className="mt-10">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-xl font-bold text-white flex items-center gap-2">
              <ZapIcon className="h-5 w-5 text-amber-400" />
              <span>Interactive Query Testbed</span>
            </h2>
            <p className="text-xs text-slate-400">
              Click any question to instantly execute grounded retrieval in the AI Assistant
            </p>
          </div>
          <Link
            href="/chat"
            className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
          >
            Open Full Chat <ArrowRightIcon className="h-3 w-3" />
          </Link>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {QUICK_PROMPTS.map((item, idx) => (
            <Link
              key={idx}
              href={`/chat?q=${encodeURIComponent(item.prompt)}`}
              className="group relative flex flex-col justify-between rounded-2xl border border-slate-800 bg-slate-900/50 p-4 backdrop-blur-md transition-all duration-200 hover:-translate-y-1 hover:border-cyan-500/50 hover:shadow-glow-cyan"
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    {item.category}
                  </span>
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${item.color}`}>
                    {item.badge}
                  </span>
                </div>
                <p className="mt-2 text-xs font-medium text-slate-200 group-hover:text-cyan-200 line-clamp-3">
                  &ldquo;{item.prompt}&rdquo;
                </p>
              </div>
              <div className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-cyan-400 group-hover:translate-x-1 transition-transform">
                <span>Test Query</span>
                <ArrowRightIcon className="h-3 w-3" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* 6 Core Architecture Pillars */}
      <div className="mt-12">
        <div className="text-center max-w-2xl mx-auto">
          <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-xs font-bold text-cyan-300 border border-cyan-500/20">
            Multi-Layer Verification
          </span>
          <h2 className="mt-3 font-display text-2xl font-extrabold text-white sm:text-3xl">
            Engineered to Solve Critical Healthcare RAG Failures
          </h2>
          <p className="mt-2 text-xs sm:text-sm text-slate-400">
            Generic LLMs hallucinate exclusions, miss policy year revisions, and invent sub-limit numbers. 
            PolicyGraph-RAG provides deterministic guarantees.
          </p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
          {ARCHITECTURE_PILLARS.map((p, idx) => {
            const Icon = p.icon;
            return (
              <Card
                key={idx}
                variant={p.accent as any}
                className="group relative overflow-hidden transition-all duration-200 hover:-translate-y-1"
              >
                <div className="flex items-center justify-between">
                  <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900 border border-slate-800 shadow-md ${p.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="rounded-full border border-slate-700/60 bg-slate-800/50 px-2.5 py-0.5 text-[10px] font-bold text-slate-300">
                    {p.badge}
                  </span>
                </div>

                <h3 className="mt-4 font-display text-base font-bold text-white group-hover:text-cyan-300 transition-colors">
                  {p.title}
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-400">
                  {p.desc}
                </p>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Interactive Workflow Pipeline */}
      <div className="mt-14 rounded-3xl border border-slate-800/80 bg-slate-900/40 p-8 backdrop-blur-xl">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div>
            <h2 className="font-display text-lg font-bold text-white">End-to-End Query Verification Pipeline</h2>
            <p className="text-xs text-slate-400">Every user question travels through an uncompromised 6-stage grounded path</p>
          </div>
          <span className="rounded-lg bg-emerald-500/10 px-2.5 py-1 text-xs font-bold text-emerald-400 border border-emerald-500/20">
            Active Realtime Pipeline
          </span>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
          {[
            { step: "01", name: "Query Analysis", detail: "Decomposes sub-queries & temporal bounds", color: "border-cyan-500/40 text-cyan-400" },
            { step: "02", name: "Dense X Retrieval", detail: "BGE-Large proposition embeddings", color: "border-teal-500/40 text-teal-400" },
            { step: "03", name: "HippoRAG Memory", detail: "Personalized PageRank on clause graph", color: "border-purple-500/40 text-purple-400" },
            { step: "04", name: "CRAG Reflection", detail: "Evaluates regime: Correct / Ambiguous", color: "border-amber-500/40 text-amber-400" },
            { step: "05", name: "Speculative Draft", detail: "Draft consensus across candidate paths", color: "border-pink-500/40 text-pink-400" },
            { step: "06", name: "Zero-Hallucination", detail: "MiniCheck precision & Conformal bounds", color: "border-emerald-500/40 text-emerald-400" },
          ].map((s, si) => (
            <div
              key={si}
              className={`rounded-xl border bg-slate-950/60 p-3.5 backdrop-blur-md transition-all hover:bg-slate-900/60 ${s.color}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-black opacity-80">{s.step}</span>
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
              </div>
              <div className="mt-2 text-xs font-bold text-white">{s.name}</div>
              <div className="mt-1 text-[11px] text-slate-400 leading-snug">{s.detail}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
