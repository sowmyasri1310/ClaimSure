"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Copy, Check, ChevronLeft, Scale, ShieldAlert, Award, FileCheck } from "lucide-react";
import Link from "next/link";

function parseReasoning(reasoningStr: string) {
  const patientEvidence: string[] = [];
  const insurerEvidence: string[] = [];
  const addedReasons: string[] = [];
  const deductedReasons: string[] = [];
  
  if (!reasoningStr) {
    return { patientEvidence, insurerEvidence, addedReasons, deductedReasons };
  }
  
  const lines = reasoningStr.split("\n");
  let currentSection = "";
  
  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("#### ")) {
      currentSection = trimmed.toLowerCase();
      continue;
    }
    
    if (trimmed.startsWith("-") || trimmed.startsWith("*")) {
      const bulletText = trimmed.replace(/^[\-\*\s•\d\.]+|[\:\-]+.*$/g, "").trim();
      if (!bulletText) continue;
      
      const lowerText = bulletText.toLowerCase();
      if (lowerText.includes("no specific evidence") || 
          lowerText.includes("no points") ||
          lowerText.includes("no reason")) {
        continue;
      }
      
      if (currentSection.includes("evidence helping the patient")) {
        patientEvidence.push(bulletText);
      } else if (currentSection.includes("evidence helping the insurer")) {
        insurerEvidence.push(bulletText);
      } else if (currentSection.includes("points added reasons")) {
        addedReasons.push(bulletText);
      } else if (currentSection.includes("points deducted reasons")) {
        deductedReasons.push(bulletText);
      }
    }
  }
  
  return { patientEvidence, insurerEvidence, addedReasons, deductedReasons };
}

function generateKeyFinding(strength: string, score: number, mismatchFound: boolean, misappliedClause?: string) {
  const cleanStrength = strength.toLowerCase();
  
  if (mismatchFound) {
    const clauseText = misappliedClause ? ` regarding ${misappliedClause}` : "";
    return `We identified a clear mismatch between your policy terms and the insurer's rejection reason${clauseText}. Our audit indicates that the insurer misapplied this policy guideline, which directly contradicts the evidence in your documents. This suggests a high likelihood of a successful appeal, and we recommend proceeding with the generated appeal letter.`;
  }
  
  if (cleanStrength === "weak") {
    return `The insurer's rejection is fully consistent with the active terms, waiting periods, or exclusions defined in your policy documents. We did not find any policy mismatch or timeline violation. Based on the current evidence, the rejection appears valid and an appeal is unlikely to succeed.`;
  }
  
  if (cleanStrength === "moderate") {
    return `While there is no technical mismatch, there are notable ambiguities in the policy wording or guidelines. Both sides have reasonable arguments, making the claim standing moderate. Proceeding with an appeal is possible but will require clarification of these ambiguous terms.`;
  }
  
  return `The case has strong standing because the medical documentation shows compelling necessity or exception criteria were met, such as an emergency exception. Although no direct policy clause mismatch was flagged, the insurer failed to consider these critical clinical circumstances, making an appeal highly recommended.`;
}

export default function DisputeResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<any>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("claimsure_dispute_result");
      if (stored) {
        try {
          setResult(JSON.parse(stored));
        } catch (e) {
          console.error("Failed to parse stored dispute result", e);
          router.push("/dispute");
        }
      } else {
        router.push("/dispute");
      }
    }
  }, [router]);

  const handleCopy = () => {
    if (result?.dispute_letter) {
      navigator.clipboard.writeText(result.dispute_letter);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!result) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-2">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-500 text-sm">Loading dispute case analysis...</p>
      </div>
    );
  }

  const score = result.dispute_score ?? 0;
  const strength = result.strength ?? "moderate";
  const confidence = result.confidence_score ?? 0;
  const faithfulness = result.faithfulness_score ?? 0;
  const hallucination = result.hallucination_risk ?? 0;

  const parsed = parseReasoning(result.score_reasoning);
  const keyEvidencePoints: string[] = [
    ...parsed.patientEvidence,
    ...parsed.insurerEvidence,
    ...parsed.addedReasons,
    ...parsed.deductedReasons
  ].slice(0, 5);

  if (keyEvidencePoints.length < 3) {
    if (result.mismatch_explanation) {
      keyEvidencePoints.push(result.mismatch_explanation);
    }
    const defaultPoints = [
      "Cross-referenced patient's hospital bill and medical records against the policy terms.",
      "Validated claim rejection reason against coverage inclusions, exclusions, and waiting periods.",
      "Assessed clinical necessity and documentation quality."
    ];
    for (const pt of defaultPoints) {
      if (keyEvidencePoints.length >= 3) break;
      keyEvidencePoints.push(pt);
    }
  }

  const keyFindingText = generateKeyFinding(strength, score, result.mismatch_found, result.misapplied_clause);
  
  // Choose colors based on strength rating
  const getStrengthMeta = (str: string) => {
    switch (str.toLowerCase()) {
      case "strong":
        return {
          bg: "bg-emerald-50 text-emerald-800 border-emerald-200",
          progress: "text-emerald-500",
          glow: "shadow-emerald-100",
          text: "High probability of approval. Mismatch detected."
        };
      case "moderate":
        return {
          bg: "bg-amber-50 text-amber-800 border-amber-200",
          progress: "text-amber-500",
          glow: "shadow-amber-100",
          text: "Moderate claim standing. Policy terms are ambiguous."
        };
      case "weak":
      default:
        return {
          bg: "bg-rose-50 text-rose-800 border-rose-200",
          progress: "text-rose-500",
          glow: "shadow-rose-100",
          text: "Low dispute strength. Rejection is supported by policy."
        };
    }
  };

  const meta = getStrengthMeta(strength);
  const strokeDashoffset = 251.2 - (251.2 * score) / 100;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8">
      {/* Back CTA */}
      <Link
        href="/dispute"
        className="inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-slate-700 transition"
      >
        <ChevronLeft className="h-4 w-4" /> Back to Upload
      </Link>

      {/* Main Results Layout Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Col: Analysis & Score Metrics (5 Columns) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 flex flex-col items-center text-center">
            <span className="text-xs font-bold text-slate-400 tracking-widest uppercase mb-4">
              Dispute Success Rating
            </span>

            {/* SVG Visual Circular Gauge */}
            <div className="relative flex items-center justify-center mb-4">
              <svg className="w-36 h-36 transform -rotate-90">
                {/* Background Ring */}
                <circle
                  cx="72"
                  cy="72"
                  r="40"
                  className="text-slate-100"
                  strokeWidth="8"
                  stroke="currentColor"
                  fill="transparent"
                />
                {/* Active Score Ring */}
                <circle
                  cx="72"
                  cy="72"
                  r="40"
                  className={`${meta.progress} transition-all duration-1000`}
                  strokeWidth="8"
                  strokeDasharray="251.2"
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="transparent"
                />
              </svg>
              {/* Central Text */}
              <div className="absolute flex flex-col items-center">
                <span className="text-4xl font-extrabold text-slate-900">{score}</span>
                <span className="text-[10px] font-bold text-slate-400">SCORE</span>
              </div>
            </div>

            {/* Strength Badge */}
            <div className={`px-4 py-1.5 border rounded-full text-xs font-black uppercase tracking-wider mb-3 ${meta.bg}`}>
              {strength} case
            </div>

            <p className="text-slate-500 text-xs px-4 leading-relaxed">{meta.text}</p>
          </div>

          {/* Supplemental Quality Metrics Card */}
          <div className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 space-y-6">
            <h3 className="font-bold text-slate-800 text-xs border-b border-slate-100 pb-3 uppercase tracking-wider text-center">
              Analysis Quality Metrics
            </h3>
            
            <div className="grid grid-cols-3 gap-4 text-center">
              {/* Confidence Metric */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Confidence</span>
                <div className="text-2xl font-black text-indigo-600">{confidence}%</div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-indigo-600 h-full rounded-full" style={{ width: `${confidence}%` }} />
                </div>
              </div>

              {/* Faithfulness Metric */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Faithfulness</span>
                <div className="text-2xl font-black text-emerald-600">{faithfulness}%</div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${faithfulness}%` }} />
                </div>
              </div>

              {/* Hallucination Risk Metric */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-400 block uppercase">Hallucination Risk</span>
                <div className="text-2xl font-black text-rose-600">{hallucination}%</div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-rose-500 h-full rounded-full" style={{ width: `${hallucination}%` }} />
                </div>
              </div>
            </div>

            {/* Metrics Explanations */}
            <div className="pt-4 border-t border-slate-50 space-y-3.5 text-left text-xs">
              <div>
                <span className="font-bold text-slate-700 block">Confidence:</span>
                <span className="text-slate-500 font-medium">How certain the system is about the dispute outcome.</span>
              </div>
              <div>
                <span className="font-bold text-slate-700 block">Faithfulness:</span>
                <span className="text-slate-500 font-medium">How strongly the analysis is supported by uploaded documents.</span>
              </div>
              <div>
                <span className="font-bold text-slate-700 block">Hallucination Risk:</span>
                <span className="text-slate-500 font-medium">Likelihood of unsupported AI-generated conclusions.</span>
              </div>
            </div>
          </div>

          {/* Audit Details */}
          <div className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 space-y-6">
            <h3 className="font-bold text-slate-800 border-b border-slate-100 pb-3 flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-indigo-600" /> Dispute Case Findings
            </h3>

            {/* 1. Key Finding */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase block tracking-wider">Key Finding</span>
              <p className="text-xs text-slate-600 leading-relaxed font-medium">
                {keyFindingText}
              </p>
            </div>

            {/* 2. Why This Decision Was Made */}
            <div className="space-y-2.5 pt-3 border-t border-slate-50">
              <span className="text-[10px] font-bold text-slate-400 uppercase block tracking-wider">Why This Decision Was Made</span>
              <ul className="space-y-2.5">
                {keyEvidencePoints.map((point: string, idx: number) => (
                  <li key={idx} className="flex gap-2 items-start text-xs text-slate-600">
                    <span className="text-indigo-500 font-black flex-shrink-0 mt-0.5">•</span>
                    <span className="leading-relaxed font-medium">{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* 3. Relevant Policy Clauses */}
            <div className="space-y-2.5 pt-3 border-t border-slate-50">
              <span className="text-[10px] font-bold text-slate-400 uppercase block tracking-wider">Relevant Policy Clauses</span>
              {result.citations && result.citations.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {result.citations.map((cite: string, idx: number) => {
                    const cleanCite = cite.replace(/^[\-\*\s•\d\.]+|[\:\-]+.*$/g, "").trim();
                    return (
                      <span key={idx} className="text-xs font-mono bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg text-slate-600 font-bold">
                        {cleanCite}
                      </span>
                    );
                  })}
                </div>
              ) : (
                <span className="text-xs text-slate-400 italic">No specific policy clauses cited.</span>
              )}
            </div>
          </div>
        </div>

        {/* Right Col: Appeal Letter Editor (7 Columns) */}
        <div className="lg:col-span-7 bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden flex flex-col">
          {/* Letter header */}
          <div className="bg-gradient-to-r from-blue-900 to-indigo-950 px-6 py-4 flex items-center justify-between text-white">
            <div className="flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-emerald-400" />
              <h3 className="font-bold text-sm">Generated Appeal Letter</h3>
            </div>
            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs bg-white/10 hover:bg-white/20 border border-white/10 py-1.5 px-3 rounded-lg transition font-semibold"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" /> Copy Letter
                </>
              )}
            </button>
          </div>

          {/* Letter Body */}
          <div className="p-8 bg-slate-50/50 flex-grow font-mono text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-[500px] overflow-y-auto border-b border-slate-100">
            {result.dispute_letter}
          </div>

          {/* Disclaimer warning footer */}
          <div className="bg-amber-50 p-4 border-l-4 border-amber-500 text-xs text-amber-900 leading-relaxed">
            <strong>Disclaimer:</strong> This letter was generated with AI assistance and should be reviewed and verified by the patient before submission.
          </div>
        </div>
      </div>
    </div>
  );
}
