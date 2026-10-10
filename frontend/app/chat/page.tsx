"use client";
import { useState, useRef, useEffect } from "react";
import Card from "@/components/Card";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import { askQuestion, streamQuestion, listPolicies } from "@/services/api";
import type { ChatQueryResponse, EvidenceItem, Policy } from "@/types";
import {
  SparklesIcon,
  ShieldCheckIcon,
  BrainIcon,
  NetworkIcon,
  ActivityIcon,
  FileTextIcon,
  AlertTriangleIcon,
  ZapIcon,
  UserIcon,
} from "@/components/Icons";

interface Message {
  role: "user" | "assistant";
  question?: string;
  response?: ChatQueryResponse;
  isStreaming?: boolean;
  liveStatus?: string;
  liveStage?: "analyzing" | "retrieving" | "graph" | "evaluating" | "generating" | "verifying";
  hallucinationAudit?: {
    detected: number;
    unsupported_numbers: string[];
    stripped_claims: string[];
    notes: string[];
  };
}

const SAMPLE_QUESTIONS = [
  "What is the waiting period for pre-existing diseases (PED)?",
  "Are modern robotic surgeries and laser eye treatments covered?",
  "What are the room rent capping and ICU charges limits?",
  "Does the policy require co-payment for senior citizens above 60?",
];

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>("");
  const [asOfDate, setAsOfDate] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listPolicies().then(setPolicies).catch(() => setPolicies([]));
  }, []);

  // Handle URL query parameter ?q=...
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("q");
      if (q && messages.length === 0) {
        setInput(q);
      }
    }
  }, [messages.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleAsk(e?: React.FormEvent, customQuestion?: string) {
    if (e) e.preventDefault();
    const query = (customQuestion || input).trim();
    if (!query || loading) return;

    setInput("");
    setLoading(true);

    if (useStreaming) {
      await handleStreamAsk(query);
    } else {
      await handleStandardAsk(query);
    }
  }

  async function handleStandardAsk(question: string) {
    setMessages((m) => [...m, { role: "user", question }]);
    try {
      const response = await askQuestion({
        question,
        policy_id: selectedPolicyId || undefined,
        as_of_date: asOfDate || undefined,
      });
      setMessages((m) => [...m, { role: "assistant", response }]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          response: {
            answer: "Could not connect to the PolicyGraph backend API. Please ensure the backend is running on port 8000.",
            policy_version: null,
            evidence: [],
            confidence: 0,
            warnings: ["Backend connection error: Check FastAPI server."],
          },
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleStreamAsk(question: string) {
    setMessages((m) => [
      ...m,
      { role: "user", question },
      {
        role: "assistant",
        isStreaming: true,
        liveStatus: "Decomposing query & analyzing temporal bounds...",
        liveStage: "analyzing",
        response: {
          answer: "",
          policy_version: null,
          evidence: [],
          confidence: 0,
          warnings: [],
        },
      },
    ]);

    let accumulatedAnswer = "";
    let accumulatedEvidence: EvidenceItem[] = [];
    let reasoningPaths: string[] = [];
    let communitySummaries: string[] = [];
    let cragRegime: "correct" | "ambiguous" | "incorrect" | undefined;
    let retrievalStrategy: string | undefined;

    try {
      await streamQuestion(
        {
          question,
          policy_id: selectedPolicyId || undefined,
          as_of_date: asOfDate || undefined,
        },
        (event, data) => {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (!last || last.role !== "assistant") return prev;

            const updated = { ...last };
            const currResp = updated.response || {
              answer: "",
              policy_version: null,
              evidence: [],
              confidence: 0,
              warnings: [],
            };

            if (event === "status") {
              updated.liveStatus = data.message || "Processing grounded retrieval...";
            } else if (event === "query_analysis") {
              retrievalStrategy = `adaptive_${data.complexity}`;
              updated.liveStage = "retrieving";
              updated.liveStatus = `Query analyzed: ${data.complexity} (${data.sub_queries?.length || 1} sub-queries)`;
            } else if (event === "evidence") {
              accumulatedEvidence = (data.evidence || []).map((ev: any) => ({
                chunk_id: ev.chunk_id,
                content: ev.content,
                page: ev.page,
                section: ev.section,
                policy_version: "active",
                relevance_score: ev.relevance_score,
              }));
              reasoningPaths = data.reasoning_paths || [];
              communitySummaries = data.community_summaries || [];
              currResp.evidence = accumulatedEvidence;
              currResp.reasoning_paths = reasoningPaths;
              currResp.community_summaries = communitySummaries;
              updated.liveStage = "graph";
              updated.liveStatus = `Retrieved ${accumulatedEvidence.length} grounded policy clauses`;
            } else if (event === "crag_evaluation") {
              cragRegime = data.regime;
              currResp.crag_regime = cragRegime;
              updated.liveStage = "evaluating";
              updated.liveStatus = `CRAG Regime: ${data.regime?.toUpperCase()}`;
            } else if (event === "token") {
              accumulatedAnswer += data.token || "";
              currResp.answer = accumulatedAnswer;
              updated.liveStage = "generating";
              updated.liveStatus = undefined;
            } else if (event === "verification") {
              currResp.factual_precision = data.factual_precision;
              currResp.calibrated_confidence = data.calibrated_confidence;
              currResp.should_abstain = data.should_abstain;
              currResp.coverage_guarantee = data.coverage_guarantee;
              currResp.entropy_level = data.entropy_level;
              currResp.verified_claims = data.verified_claims;
              if (data.warnings) currResp.warnings = data.warnings;
              updated.liveStage = "verifying";
            } else if (event === "hallucination_audit") {
              updated.hallucinationAudit = data;
              if (data.notes) currResp.warnings = [...(currResp.warnings || []), ...data.notes];
            } else if (event === "done") {
              updated.isStreaming = false;
              updated.liveStatus = undefined;
              if (data.answer) currResp.answer = data.answer;
              currResp.confidence = data.confidence ?? currResp.confidence;
              currResp.calibrated_confidence = data.calibrated_confidence ?? currResp.calibrated_confidence;
              currResp.should_abstain = data.should_abstain ?? currResp.should_abstain;
              currResp.coverage_guarantee = data.coverage_guarantee ?? currResp.coverage_guarantee;
              currResp.policy_version = data.policy_version ?? currResp.policy_version;
              if (data.warnings) currResp.warnings = data.warnings;
            }

            updated.response = { ...currResp, retrieval_strategy: retrievalStrategy };
            return [...prev.slice(0, -1), updated];
          });
        },
        (err) => {
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (!last || last.role !== "assistant") return prev;
            return [
              ...prev.slice(0, -1),
              {
                role: "assistant",
                isStreaming: false,
                response: {
                  answer: "Streaming connection error: " + err.message,
                  policy_version: null,
                  evidence: [],
                  confidence: 0,
                  warnings: ["Stream disconnected or interrupted"],
                },
              },
            ];
          });
        }
      );
    } catch {
      // Handled in onError
    } finally {
      setLoading(false);
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.isStreaming) {
          return [...prev.slice(0, -1), { ...last, isStreaming: false, liveStatus: undefined }];
        }
        return prev;
      });
    }
  }

  return (
    <div className="mx-auto flex h-screen max-w-5xl flex-col px-4 py-5 lg:px-8">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-xl font-bold text-white sm:text-2xl">
              Policy Research Assistant
            </h1>
            <span className="rounded-full bg-cyan-500/10 px-2.5 py-0.5 text-[10px] font-bold text-cyan-300 border border-cyan-500/30">
              Agentic RAG
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Bi-Temporal Grounding · HippoRAG Associative Memory · Zero-Hallucination Shield
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Policy Selector */}
          <select
            className="rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
            value={selectedPolicyId}
            onChange={(e) => setSelectedPolicyId(e.target.value)}
          >
            <option value="">All Indexed Policies</option>
            {policies.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.insurer})
              </option>
            ))}
          </select>

          {/* Temporal Admission Date */}
          <input
            type="date"
            title="As-of Policy Validity Date"
            value={asOfDate}
            onChange={(e) => setAsOfDate(e.target.value)}
            className="rounded-xl border border-slate-700 bg-slate-900/90 px-2.5 py-1.5 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          />

          {/* SSE Toggle */}
          <label className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 px-2.5 py-1.5 text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={useStreaming}
              onChange={(e) => setUseStreaming(e.target.checked)}
              className="rounded border-slate-700 text-cyan-500 focus:ring-0"
            />
            <span className="text-[11px] font-medium">SSE Stream</span>
          </label>
        </div>
      </div>

      {/* Messages Thread */}
      <div className="mt-4 flex-1 space-y-5 overflow-y-auto pr-1">
        {messages.length === 0 && (
          <div className="mt-6 rounded-3xl border border-slate-800/80 bg-gradient-to-b from-slate-900/60 to-slate-950/80 p-8 text-center backdrop-blur-xl">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-500 to-teal-400 p-0.5 shadow-glow-cyan">
              <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-slate-950">
                <SparklesIcon className="h-7 w-7 text-cyan-400" />
              </div>
            </div>

            <h2 className="mt-4 font-display text-lg font-bold text-white">
              Ask Any Healthcare Insurance Policy Question
            </h2>
            <p className="mt-1 max-w-md mx-auto text-xs text-slate-400">
              Queries are synthesized strictly against grounded clauses. Hallucinations are actively intercepted.
            </p>

            <div className="mt-6 grid grid-cols-1 gap-2.5 sm:grid-cols-2 text-left max-w-2xl mx-auto">
              {SAMPLE_QUESTIONS.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAsk(undefined, q)}
                  className="group flex items-start gap-2.5 rounded-xl border border-slate-800/80 bg-slate-900/50 p-3 text-xs text-slate-300 hover:border-cyan-500/50 hover:bg-slate-900 hover:text-white transition-all text-left"
                >
                  <ZapIcon className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                  <span>&ldquo;{q}&rdquo;</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-auto flex max-w-2xl items-end justify-end gap-2.5">
              <div className="rounded-2xl rounded-tr-sm bg-gradient-to-r from-cyan-600 to-teal-600 px-4 py-3 text-sm font-medium text-white shadow-lg shadow-cyan-950/40">
                <p className="leading-relaxed">{m.question}</p>
              </div>
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-700/50 border border-cyan-400/30 text-white">
                <UserIcon className="h-4 w-4" />
              </div>
            </div>
          ) : (
            <div key={i} className="flex max-w-4xl items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 p-0.5 shadow-glow-cyan">
                <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-slate-950">
                  <ShieldCheckIcon className="h-5 w-5 text-cyan-400" />
                </div>
              </div>

              <Card className="flex-1 overflow-hidden border-slate-800/80 bg-slate-900/70 p-5 shadow-2xl backdrop-blur-2xl">
                {/* Live Status Banner during streaming */}
                {m.liveStatus && (
                  <div className="mb-4 flex items-center gap-2.5 rounded-xl border border-cyan-500/30 bg-cyan-950/40 px-3.5 py-2 text-xs text-cyan-300 shadow-glow-cyan">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-75" />
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-cyan-500" />
                    </span>
                    <span className="font-medium">{m.liveStatus}</span>
                  </div>
                )}

                {/* Main Synthesized Answer */}
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
                  {m.response?.answer || (m.isStreaming ? "Synthesizing evidence-verified answer..." : "")}
                  {m.isStreaming && (
                    <span className="inline-block w-2 h-4 ml-1.5 bg-cyan-400 animate-pulse align-middle" />
                  )}
                </div>

                {/* Metrics & Badges Bar */}
                <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-800 pt-3">
                  {m.response && (
                    <ConfidenceBadge
                      score={m.response.calibrated_confidence ?? m.response.confidence}
                      isCalibrated={m.response.calibrated_confidence !== undefined}
                      coverageGuarantee={m.response.coverage_guarantee}
                      shouldAbstain={m.response.should_abstain}
                      entropyLevel={m.response.entropy_level}
                    />
                  )}

                  {m.response?.crag_regime && (
                    <span
                      className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                        m.response.crag_regime === "correct"
                          ? "border-emerald-500/40 bg-emerald-950/60 text-emerald-300"
                          : m.response.crag_regime === "ambiguous"
                          ? "border-amber-500/40 bg-amber-950/60 text-amber-300"
                          : "border-rose-500/40 bg-rose-950/60 text-rose-300"
                      }`}
                    >
                      CRAG: {m.response.crag_regime.toUpperCase()}
                    </span>
                  )}

                  {m.response?.factual_precision !== undefined && (
                    <span className="rounded-full border border-blue-500/30 bg-blue-950/50 px-2.5 py-0.5 text-xs font-medium text-blue-300">
                      MiniCheck: {Math.round(m.response.factual_precision * 100)}%
                    </span>
                  )}

                  {m.response?.speculative_drafts_count ? (
                    <span className="rounded-full border border-purple-500/30 bg-purple-950/50 px-2.5 py-0.5 text-xs font-medium text-purple-300">
                      Speculative: {m.response.speculative_drafts_count} Drafts
                    </span>
                  ) : null}

                  {m.response?.policy_version && (
                    <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-0.5 text-xs text-slate-300">
                      {m.response.policy_version}
                    </span>
                  )}
                </div>

                {/* Zero-Hallucination Shield Notification */}
                {m.hallucinationAudit && m.hallucinationAudit.detected > 0 && (
                  <div className="mt-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/30 p-3 text-xs text-emerald-300">
                    <div className="flex items-center gap-1.5 font-bold text-emerald-200">
                      <ShieldCheckIcon className="h-4 w-4 text-emerald-400" />
                      <span>Zero-Hallucination Shield Active: Neutralized {m.hallucinationAudit.detected} Assertions</span>
                    </div>
                    <p className="mt-1 text-slate-300 text-[11px] leading-relaxed">
                      Ungrounded claims were purged before presentation. Response adheres strictly to verified policy text.
                    </p>
                    {m.hallucinationAudit.unsupported_numbers.length > 0 && (
                      <div className="mt-1 font-mono text-[11px] text-amber-300">
                        Excluded unverified numbers: {m.hallucinationAudit.unsupported_numbers.join(", ")}
                      </div>
                    )}
                  </div>
                )}

                {/* Warnings Alert */}
                {m.response?.warnings && m.response.warnings.length > 0 && (
                  <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-950/30 p-3 text-xs text-amber-300">
                    <div className="flex items-center gap-1 font-bold text-amber-200">
                      <AlertTriangleIcon className="h-4 w-4 text-amber-400" />
                      <span>Verification Notes</span>
                    </div>
                    <ul className="mt-1 space-y-1 text-[11px] text-amber-200/90 pl-5 list-disc">
                      {m.response.warnings.map((w, wi) => (
                        <li key={wi}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* GraphRAG Communities Box */}
                {m.response?.community_summaries && m.response.community_summaries.length > 0 && (
                  <div className="mt-3 rounded-xl border border-purple-500/20 bg-purple-950/30 p-3 text-xs text-purple-200">
                    <div className="flex items-center gap-1.5 font-bold text-purple-300">
                      <NetworkIcon className="h-4 w-4 text-purple-400" />
                      <span>GraphRAG Leiden Community Insights</span>
                    </div>
                    <div className="mt-1.5 space-y-1 text-slate-300 text-[11px]">
                      {m.response.community_summaries.map((comm, ci) => (
                        <div key={ci}>• {comm}</div>
                      ))}
                    </div>
                  </div>
                )}

                {/* HippoRAG Reasoning Paths */}
                {m.response?.reasoning_paths && m.response.reasoning_paths.length > 0 && (
                  <div className="mt-2.5 rounded-xl border border-slate-800 bg-slate-950/60 p-2.5 text-[11px] text-slate-400">
                    <span className="font-semibold text-cyan-300">HippoRAG Graph Associations: </span>
                    {m.response.reasoning_paths.slice(0, 3).join(" ➔ ")}
                  </div>
                )}

                {/* Verified Claims Breakdown (Collapsible) */}
                {m.response?.verified_claims && m.response.verified_claims.length > 0 && (
                  <details className="mt-3 text-xs group">
                    <summary className="cursor-pointer font-semibold text-slate-400 hover:text-cyan-300 transition-colors select-none">
                      Atomic Claim Grounding Breakdown ({m.response.verified_claims.length} claims verified)
                    </summary>
                    <div className="mt-2.5 space-y-1.5 pl-3 border-l-2 border-slate-800">
                      {m.response.verified_claims.map((c, ci) => (
                        <div key={ci} className="flex items-start gap-2">
                          <span
                            className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${
                              c.status === "SUPPORTED"
                                ? "bg-emerald-950 text-emerald-300 border border-emerald-500/30"
                                : c.status === "PARTIALLY_SUPPORTED"
                                ? "bg-amber-950 text-amber-300 border border-amber-500/30"
                                : "bg-rose-950 text-rose-300 border border-rose-500/30"
                            }`}
                          >
                            {c.status}
                          </span>
                          <span className="text-slate-300 text-[11px]">{c.claim}</span>
                        </div>
                      ))}
                    </div>
                  </details>
                )}

                {/* Supporting Policy Evidence Clauses (Collapsible) */}
                {m.response?.evidence && m.response.evidence.length > 0 && (
                  <details className="mt-3.5 group">
                    <summary className="cursor-pointer text-xs font-bold text-cyan-400 hover:text-cyan-300 transition-colors select-none flex items-center gap-1.5">
                      <FileTextIcon className="h-4 w-4" />
                      <span>Supporting Policy Evidence ({m.response.evidence.length} grounded clauses)</span>
                    </summary>
                    <div className="mt-3 space-y-2 max-h-80 overflow-y-auto pr-1">
                      {m.response.evidence.map((ev, ei) => (
                        <div
                          key={ei}
                          className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs text-slate-300 transition-all hover:border-slate-700"
                        >
                          <div className="mb-1.5 flex items-center justify-between text-[11px] text-slate-400">
                            <span className="font-semibold text-cyan-300">
                              Page {ev.page ?? "?"} · {ev.section ?? "Contract Clause"}
                            </span>
                            <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-cyan-300 border border-slate-700">
                              Score: {ev.relevance_score}
                            </span>
                          </div>
                          <div className="text-[11px] leading-relaxed text-slate-300 line-clamp-3 hover:line-clamp-none">
                            {ev.content}
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </Card>
            </div>
          )
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box Form */}
      <form onSubmit={handleAsk} className="mt-4 flex gap-2 border-t border-slate-800/80 pt-3">
        <input
          className="flex-1 rounded-2xl border border-slate-700 bg-slate-900/90 px-4 py-3 text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20"
          placeholder="Ask a policy question (e.g. waiting periods, ICU limits, cataract sub-limit, co-pay)..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="inline-flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-teal-500 px-6 py-3 text-sm font-bold text-slate-950 shadow-glow-cyan transition-all duration-200 hover:from-cyan-400 hover:to-teal-400 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <span className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
              <span>Grounded...</span>
            </>
          ) : (
            <>
              <SparklesIcon className="h-4 w-4" />
              <span>Ask</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
