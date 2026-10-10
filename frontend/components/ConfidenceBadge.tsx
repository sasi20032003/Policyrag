import React from "react";

export default function ConfidenceBadge({
  score,
  isCalibrated = false,
  coverageGuarantee,
  shouldAbstain = false,
  entropyLevel,
}: {
  score: number;
  isCalibrated?: boolean;
  coverageGuarantee?: number;
  shouldAbstain?: boolean;
  entropyLevel?: "low" | "medium" | "high";
}) {
  const pct = Math.round(score * 100);

  if (shouldAbstain) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/40 bg-rose-950/60 px-3 py-1 text-xs font-semibold text-rose-300 shadow-glow-rose backdrop-blur-md">
        <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping" />
        <span>Abstained (Uncertain · {pct}%)</span>
      </span>
    );
  }

  // Color schemes based on score
  const isHigh = pct >= 75;
  const isMed = pct >= 50;

  const badgeTheme = isHigh
    ? {
        bg: "bg-emerald-950/60 border-emerald-500/40 text-emerald-300 shadow-glow-emerald",
        dot: "bg-emerald-400",
        label: "Verified High",
      }
    : isMed
    ? {
        bg: "bg-amber-950/60 border-amber-500/40 text-amber-300",
        dot: "bg-amber-400",
        label: "Moderate",
      }
    : {
        bg: "bg-rose-950/60 border-rose-500/40 text-rose-300 shadow-glow-rose",
        dot: "bg-rose-400",
        label: "Low Grounding",
      };

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium backdrop-blur-md transition-all ${badgeTheme.bg}`}
      title={
        isCalibrated && coverageGuarantee
          ? `Conformal Risk Calibration: ${Math.round(coverageGuarantee * 100)}% statistical coverage guarantee (Entropy: ${entropyLevel || "low"})`
          : `Grounded confidence: ${pct}%`
      }
    >
      <span className={`h-2 w-2 rounded-full ${badgeTheme.dot} ${isHigh ? "animate-pulse" : ""}`} />
      
      <span className="font-semibold">
        {isCalibrated ? "Calibrated Trust:" : "Confidence:"} {pct}%
      </span>

      {coverageGuarantee && (
        <span className="rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] text-emerald-200 border border-emerald-500/30 font-mono">
          {Math.round(coverageGuarantee * 100)}% coverage
        </span>
      )}

      {entropyLevel && entropyLevel !== "low" && (
        <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] text-amber-200 border border-amber-500/30">
          {entropyLevel} entropy
        </span>
      )}
    </span>
  );
}
