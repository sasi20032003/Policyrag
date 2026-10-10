"use client";
import { useEffect, useState } from "react";
import Card from "@/components/Card";
import ConfidenceBadge from "@/components/ConfidenceBadge";
import {
  listPatients,
  createPatient,
  deletePatient,
  chatPatient,
  listPolicies,
} from "@/services/api";
import type { PatientProfile, ChatQueryResponse, Policy } from "@/types";
import {
  UserIcon,
  SparklesIcon,
  ShieldCheckIcon,
  ActivityIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  TrashIcon,
  ZapIcon,
} from "@/components/Icons";

const DEFAULT_PRESETS = [
  {
    full_name: "Rajesh Kumar",
    age: 48,
    gender: "Male",
    policy_start_date: "2023-04-01",
    sum_insured: 500000,
    plan_type: "Family Floater",
    pre_existing_diseases: ["Type 2 Diabetes", "Hypertension"],
    current_conditions: ["Knee Pain"],
    is_diabetic: true,
    is_hypertensive: true,
    is_smoker: false,
    notes: "Completed 18 months under current policy. Inquiring about knee arthroscopy.",
  },
  {
    full_name: "Ananya Sharma",
    age: 31,
    gender: "Female",
    policy_start_date: "2024-01-10",
    sum_insured: 1000000,
    plan_type: "Individual Comprehensive",
    pre_existing_diseases: [],
    current_conditions: ["First Pregnancy - 2nd Trimester"],
    is_diabetic: false,
    is_hypertensive: false,
    is_smoker: false,
    notes: "Checking maternity benefits, newborn coverage, and waiting periods.",
  },
];

export default function PatientsPage() {
  const [patients, setPatients] = useState<PatientProfile[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<PatientProfile | null>(null);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState("");
  const [question, setQuestion] = useState("");
  const [chatResult, setChatResult] = useState<ChatQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingPreset, setSavingPreset] = useState(false);

  useEffect(() => {
    loadPatients();
    listPolicies().then(setPolicies).catch(() => setPolicies([]));
  }, []);

  async function loadPatients() {
    try {
      const data = await listPatients();
      setPatients(data);
      if (data.length > 0) {
        setSelectedPatient(data[0]);
      }
    } catch {
      setPatients([]);
    }
  }

  async function handleLoadPreset(preset: any) {
    setSavingPreset(true);
    try {
      const created = await createPatient(preset);
      await loadPatients();
      setSelectedPatient(created);
    } catch (err: any) {
      // If error or already exists
    } finally {
      setSavingPreset(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Remove this patient profile?")) return;
    try {
      await deletePatient(id);
      await loadPatients();
      setSelectedPatient(null);
    } catch {}
  }

  async function handleAskPersonalized(customQ?: string) {
    const q = (customQ || question).trim();
    if (!q || !selectedPatient || loading) return;
    setLoading(true);
    setChatResult(null);

    try {
      const res = await chatPatient({
        question: q,
        patient_profile_id: selectedPatient.id,
        policy_id: selectedPolicyId || undefined,
      });
      setChatResult(res);
    } catch {
      setChatResult({
        answer: "Could not complete personalized claim query. Please verify the backend is running.",
        policy_version: null,
        evidence: [],
        confidence: 0,
        warnings: ["Patient context resolution error."],
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
              Patient Claim & Eligibility Navigator
            </h1>
            <span className="rounded-full bg-pink-500/10 px-2.5 py-0.5 text-xs font-bold text-pink-300 border border-pink-500/30">
              Personalized Context
            </span>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-slate-400">
            Injects age, pre-existing conditions, active policy duration, and sum insured to answer personalized coverage queries.
          </p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Patient Profiles List & Quick Presets */}
        <div className="space-y-4">
          <Card className="border-slate-800 bg-slate-900/70 p-5 backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-display text-sm font-bold text-white flex items-center gap-2">
                <UserIcon className="h-4 w-4 text-cyan-400" />
                <span>Patient Profiles</span>
              </h3>
              <span className="text-[11px] font-mono text-slate-400">{patients.length} active</span>
            </div>

            {/* List */}
            <div className="mt-3 space-y-2.5 max-h-60 overflow-y-auto pr-1">
              {patients.length === 0 && (
                <p className="text-xs text-slate-500 py-3 text-center">
                  No patient profiles found. Load a sample preset below to test!
                </p>
              )}

              {patients.map((p) => {
                const isSelected = selectedPatient?.id === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPatient(p)}
                    className={`cursor-pointer rounded-xl border p-3 transition-all ${
                      isSelected
                        ? "border-cyan-500/60 bg-cyan-950/30 shadow-glow-cyan"
                        : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-xs">{p.full_name}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(p.id);
                        }}
                        className="text-slate-500 hover:text-rose-400 p-1"
                        title="Delete"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
                      <span>Age: {p.age || "?"}</span>
                      <span>·</span>
                      <span>{p.plan_type || "Floater"}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Quick Demo Presets */}
            <div className="mt-4 border-t border-slate-800 pt-3">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Load Sample Test Profiles
              </span>
              <div className="mt-2 space-y-1.5">
                {DEFAULT_PRESETS.map((preset, idx) => (
                  <button
                    key={idx}
                    disabled={savingPreset}
                    onClick={() => handleLoadPreset(preset)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-left text-xs text-slate-300 hover:border-cyan-500 hover:text-white transition-all flex items-center justify-between"
                  >
                    <span>+ {preset.full_name} ({preset.age}y, {preset.pre_existing_diseases[0] || "No PED"})</span>
                    <SparklesIcon className="h-3 w-3 text-cyan-400" />
                  </button>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* Center & Right: Selected Profile Card & Personalized Q&A */}
        <div className="lg:col-span-2 space-y-5">
          {selectedPatient ? (
            <>
              {/* Profile Overview Card */}
              <Card className="border-slate-800 bg-slate-900/70 p-6 backdrop-blur-xl">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-pink-500 to-purple-600 p-0.5 shadow-glow-purple">
                      <div className="flex h-full w-full items-center justify-center rounded-[14px] bg-slate-950 font-display font-black text-white text-base">
                        {selectedPatient.full_name.charAt(0)}
                      </div>
                    </div>
                    <div>
                      <h2 className="font-display text-lg font-bold text-white">
                        {selectedPatient.full_name}
                      </h2>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>{selectedPatient.age} years old</span>
                        <span>·</span>
                        <span>{selectedPatient.gender}</span>
                        <span>·</span>
                        <span className="text-cyan-400">{selectedPatient.plan_type}</span>
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 uppercase font-bold">Sum Insured</div>
                    <div className="font-mono text-sm font-black text-emerald-400">
                      ₹{selectedPatient.sum_insured?.toLocaleString() || "5,00,000"}
                    </div>
                  </div>
                </div>

                {/* Badges / Medical Attributes */}
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <div className="text-[10px] text-slate-500 font-bold uppercase">Pre-Existing (PED)</div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {selectedPatient.pre_existing_diseases && selectedPatient.pre_existing_diseases.length > 0 ? (
                        selectedPatient.pre_existing_diseases.map((ped, i) => (
                          <span
                            key={i}
                            className="rounded-md border border-amber-500/30 bg-amber-950/50 px-2 py-0.5 text-[10px] font-semibold text-amber-300"
                          >
                            {ped}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-500">None declared</span>
                      )}
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <div className="text-[10px] text-slate-500 font-bold uppercase">Policy Duration</div>
                    <div className="mt-1 text-xs font-semibold text-white">
                      Started: {selectedPatient.policy_start_date || "2023-04-01"}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      Active: ~{Math.max(1, new Date().getFullYear() - 2023)} years continuous
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <div className="text-[10px] text-slate-500 font-bold uppercase">Health Flags</div>
                    <div className="mt-1 flex gap-1.5 text-[10px]">
                      {selectedPatient.is_diabetic && (
                        <span className="rounded bg-rose-950 px-1.5 py-0.5 text-rose-300 border border-rose-500/30">
                          Diabetic
                        </span>
                      )}
                      {selectedPatient.is_hypertensive && (
                        <span className="rounded bg-purple-950 px-1.5 py-0.5 text-purple-300 border border-purple-500/30">
                          Hypertensive
                        </span>
                      )}
                      {!selectedPatient.is_diabetic && !selectedPatient.is_hypertensive && (
                        <span className="text-slate-500 text-xs">Standard Risk</span>
                      )}
                    </div>
                  </div>
                </div>

                {selectedPatient.notes && (
                  <p className="mt-3 text-xs text-slate-400 italic">
                    Note: &ldquo;{selectedPatient.notes}&rdquo;
                  </p>
                )}
              </Card>

              {/* Personalized Eligibility Query Simulator */}
              <Card className="border-slate-800 bg-slate-900/70 p-6 backdrop-blur-xl">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-display text-sm font-bold text-white flex items-center gap-2">
                    <SparklesIcon className="h-4 w-4 text-pink-400" />
                    <span>Personalized Claim Eligibility Check</span>
                  </h3>
                  <select
                    className="rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-300"
                    value={selectedPolicyId}
                    onChange={(e) => setSelectedPolicyId(e.target.value)}
                  >
                    <option value="">Any Policy</option>
                    {policies.map((pol) => (
                      <option key={pol.id} value={pol.id}>
                        {pol.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Quick question suggestions tailored to this patient */}
                <div className="mt-3 flex flex-wrap gap-2">
                  {[
                    `Am I eligible for surgery for ${selectedPatient.current_conditions?.[0] || "my condition"}?`,
                    "Has my pre-existing disease waiting period finished?",
                    "What co-pay or sub-limit applies to my hospital stay?",
                  ].map((sug, si) => (
                    <button
                      key={si}
                      onClick={() => handleAskPersonalized(sug)}
                      className="rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-1 text-[11px] text-slate-400 hover:border-pink-500/50 hover:text-pink-300 transition-all text-left"
                    >
                      &ldquo;{sug}&rdquo;
                    </button>
                  ))}
                </div>

                <div className="mt-4 flex gap-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder={`Ask coverage eligibility for ${selectedPatient.full_name}...`}
                    className="flex-1 rounded-xl border border-slate-700 bg-slate-950/90 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-pink-500 focus:outline-none"
                    disabled={loading}
                  />
                  <button
                    onClick={() => handleAskPersonalized()}
                    disabled={loading || !question.trim()}
                    className="rounded-xl bg-gradient-to-r from-pink-500 to-rose-500 px-5 py-2.5 text-xs font-bold text-white shadow-glow-rose hover:opacity-90 disabled:opacity-40"
                  >
                    {loading ? "Evaluating..." : "Evaluate Claim"}
                  </button>
                </div>

                {/* Result Display */}
                {chatResult && (
                  <div className="mt-5 rounded-2xl border border-pink-500/30 bg-pink-950/20 p-5 backdrop-blur-xl">
                    <div className="flex items-center justify-between border-b border-pink-500/20 pb-3">
                      <div className="flex items-center gap-2">
                        <ShieldCheckIcon className="h-5 w-5 text-emerald-400" />
                        <span className="font-bold text-sm text-white">Personalized Evaluation Result</span>
                      </div>
                      <ConfidenceBadge
                        score={chatResult.calibrated_confidence ?? chatResult.confidence}
                        isCalibrated={chatResult.calibrated_confidence !== undefined}
                        coverageGuarantee={chatResult.coverage_guarantee}
                      />
                    </div>

                    <div className="mt-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-200">
                      {chatResult.answer}
                    </div>

                    {chatResult.evidence && chatResult.evidence.length > 0 && (
                      <div className="mt-3.5 space-y-1.5 border-t border-pink-500/20 pt-3">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-pink-300">
                          Cited Contract Clauses ({chatResult.evidence.length})
                        </span>
                        {chatResult.evidence.slice(0, 2).map((ev, ei) => (
                          <div key={ei} className="rounded-lg bg-slate-950/70 p-2 text-[11px] text-slate-400 border border-slate-800">
                            Page {ev.page ?? "?"} · {ev.section ?? "Clause"}: {ev.content.slice(0, 140)}...
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            </>
          ) : (
            <div className="flex h-96 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/40 text-xs text-slate-500">
              Select or create a patient profile on the left to start personalized claim simulation.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
