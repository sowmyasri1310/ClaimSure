"use client";

import React from "react";
import { CheckCircle, XCircle, AlertTriangle, ShieldCheck } from "lucide-react";

interface ClaimResultProps {
  score: number;
  strength: "weak" | "moderate" | "strong";
  mismatchFound: boolean;
  scoreReasoning: string;
  citations: string[];
}

export default function ClaimResult({
  score,
  strength,
  mismatchFound,
  scoreReasoning,
  citations
}: ClaimResultProps) {
  const getStrengthMeta = (str: string) => {
    switch (str.toLowerCase()) {
      case "strong":
        return "bg-emerald-50 text-emerald-800 border-emerald-200";
      case "moderate":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "weak":
      default:
        return "bg-rose-50 text-rose-800 border-rose-200";
    }
  };

  return (
    <div className="bg-white rounded-3xl p-6 border border-slate-100 shadow-lg space-y-6">
      {/* Score and Strength */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div>
          <span className="text-xs text-slate-500 font-bold block mb-1">DISPUTE STANDING</span>
          <span className={`px-3 py-1 border rounded-full text-xs font-black uppercase tracking-wider ${getStrengthMeta(strength)}`}>
            {strength}
          </span>
        </div>
        <div className="text-right">
          <span className="text-xs text-slate-500 font-bold block mb-1">SCORE</span>
          <span className="text-2xl font-black text-slate-900">{score}/100</span>
        </div>
      </div>

      {/* Mismatch indicator */}
      <div className="space-y-1">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide flex items-center gap-1">
          <AlertTriangle className="h-3.5 w-3.5 text-indigo-500" /> Audit Assessment
        </span>
        <div className="flex items-center gap-2">
          {mismatchFound ? (
            <>
              <CheckCircle className="h-5 w-5 text-emerald-500" />
              <span className="text-sm font-bold text-slate-800">Policy Mismatch Detected</span>
            </>
          ) : (
            <>
              <XCircle className="h-5 w-5 text-rose-500" />
              <span className="text-sm font-bold text-slate-800">No Policy Mismatch Found</span>
            </>
          )}
        </div>
      </div>

      {/* Explanatory text */}
      <div className="space-y-1">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Analysis Reasoning</span>
        <p className="text-xs text-slate-600 leading-relaxed">{scoreReasoning}</p>
      </div>

      {/* Citations list */}
      {citations.length > 0 && (
        <div className="space-y-2 pt-3 border-t border-slate-100">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Citations</span>
          <ul className="space-y-1.5">
            {citations.map((cite, idx) => (
              <li key={idx} className="text-xs text-slate-600 flex items-start gap-1.5">
                <ShieldCheck className="h-4 w-4 text-indigo-500 mt-0.5 flex-shrink-0" />
                <span>{cite}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
