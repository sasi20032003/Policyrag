import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "glass" | "interactive" | "cyan" | "purple" | "emerald" | "amber" | "rose";
  onClick?: () => void;
}

export default function Card({
  children,
  className = "",
  variant = "glass",
  onClick,
}: CardProps) {
  const variantStyles: Record<string, string> = {
    default: "bg-slate-900/80 border-slate-800/80 text-slate-100",
    glass: "bg-slate-900/60 backdrop-blur-xl border-slate-800/80 hover:border-slate-700/80 text-slate-100 shadow-xl shadow-black/30",
    interactive: "bg-slate-900/70 backdrop-blur-xl border-slate-800 hover:border-cyan-500/50 hover:shadow-glow-cyan hover:-translate-y-0.5 transition-all duration-200 text-slate-100 cursor-pointer",
    cyan: "bg-gradient-to-br from-cyan-950/30 via-slate-900/80 to-slate-900/90 border-cyan-500/30 hover:border-cyan-400/50 hover:shadow-glow-cyan transition-all text-slate-100",
    purple: "bg-gradient-to-br from-purple-950/30 via-slate-900/80 to-slate-900/90 border-purple-500/30 hover:border-purple-400/50 hover:shadow-glow-purple transition-all text-slate-100",
    emerald: "bg-gradient-to-br from-emerald-950/30 via-slate-900/80 to-slate-900/90 border-emerald-500/30 hover:border-emerald-400/50 hover:shadow-glow-emerald transition-all text-slate-100",
    amber: "bg-gradient-to-br from-amber-950/30 via-slate-900/80 to-slate-900/90 border-amber-500/30 hover:border-amber-400/50 transition-all text-slate-100",
    rose: "bg-gradient-to-br from-rose-950/30 via-slate-900/80 to-slate-900/90 border-rose-500/30 hover:border-rose-400/50 hover:shadow-glow-rose transition-all text-slate-100",
  };

  return (
    <div
      onClick={onClick}
      className={`rounded-2xl border p-5 ${variantStyles[variant] || variantStyles.glass} ${className}`}
    >
      {children}
    </div>
  );
}
