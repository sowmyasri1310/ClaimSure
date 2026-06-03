"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import { LayoutDashboard, Scale, Calendar, ChevronRight, Loader2, AlertCircle, PlusCircle, ArrowUpRight, Trash2 } from "lucide-react";
import Link from "next/link";

interface DisputeCase {
  _id: string;
  insurer_name: string;
  dispute_score: number;
  strength: "weak" | "moderate" | "strong";
  dispute_letter: string;
  mismatch_found: boolean;
  misapplied_clause?: string;
  citations: string[];
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [authLoading, setAuthLoading] = useState(true);
  const [cases, setCases] = useState<DisputeCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Check auth and fetch history
  useEffect(() => {
    supabase.auth.getSession().then((res: any) => {
      const session = res.data?.session;
      if (!session) {
        router.push("/auth/login");
      } else {
        setAuthLoading(false);
        fetchCases();
      }
    });
  }, [router]);

  const fetchCases = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.get("/dashboard/cases");
      setCases(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load past disputes from database.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCase = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation(); // Prevent navigating to details page
    if (!window.confirm("Are you sure you want to delete this dispute case? This action cannot be undone.")) {
      return;
    }
    
    setDeletingId(caseId);
    try {
      await api.delete(`/dashboard/cases/${caseId}`);
      // Remove the deleted case from state
      setCases((prev) => prev.filter((c) => c._id !== caseId));
    } catch (err: any) {
      setError(err.message || "Failed to delete the dispute case.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleViewDetails = (c: DisputeCase) => {
    if (typeof window !== "undefined") {
      // Format case data to match dispute result route expectation
      localStorage.setItem("claimsure_dispute_result", JSON.stringify({
        mismatch_found: c.mismatch_found,
        misapplied_clause: c.misapplied_clause,
        dispute_score: c.dispute_score,
        score_reasoning: "Reviewing archived resolution record.",
        strength: c.strength,
        dispute_letter: c.dispute_letter,
        citations: c.citations
      }));
    }
    router.push("/dispute/result");
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric"
      });
    } catch {
      return "N/A";
    }
  };

  const getStrengthClass = (str: string) => {
    switch (str.toLowerCase()) {
      case "strong":
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
      case "moderate":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "weak":
      default:
        return "bg-rose-100 text-rose-800 border-rose-200";
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
        <Loader2 className="h-10 w-10 text-indigo-600 animate-spin" />
        <p className="text-slate-500 text-sm font-semibold">Checking authorization state...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-8 animate-fade-in">
      {/* Title & Call to Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 flex items-center gap-2">
            <LayoutDashboard className="h-8 w-8 text-indigo-600" />
            Cases Dashboard
          </h1>
          <p className="text-slate-600 mt-1 text-sm">
            Access, view, and print previously generated medical claims appeal audits.
          </p>
        </div>
        <Link
          href="/dispute"
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold px-5 py-3 rounded-2xl shadow transition transform hover:-translate-y-0.5 text-sm"
        >
          <PlusCircle className="h-4.5 w-4.5" /> New Dispute Case
        </Link>
      </div>

      {error && (
        <div className="bg-rose-50 border-l-4 border-rose-500 p-4 rounded-xl text-sm text-rose-800 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-rose-500 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Cases Log */}
      {loading ? (
        <div className="bg-white rounded-3xl p-12 border border-slate-100 shadow-sm flex flex-col items-center justify-center min-h-[300px]">
          <Loader2 className="h-8 w-8 text-indigo-600 animate-spin mb-2" />
          <p className="text-slate-500 text-sm">Retrieving previous case archives...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="bg-white rounded-3xl p-12 border border-slate-100 shadow-xl flex flex-col items-center justify-center text-center min-h-[350px]">
          <Scale className="h-16 w-16 text-slate-300 mb-4" />
          <h3 className="text-lg font-bold text-slate-700 mb-1.5">No Past Disputes Filed</h3>
          <p className="text-slate-500 text-sm max-w-sm mb-6">
            You haven&apos;t filed any medical claim dispute reviews yet. Let&apos;s evaluate your hospital bill.
          </p>
          <Link
            href="/dispute"
            className="inline-flex items-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 font-bold px-6 py-3 rounded-xl transition text-sm"
          >
            Create New Case <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {cases.map((c) => (
            <div
              key={c._id}
              onClick={() => handleViewDetails(c)}
              className="bg-white border border-slate-100 hover:border-indigo-200 hover:shadow-2xl rounded-3xl p-6 shadow-md transition cursor-pointer flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between gap-2 border-b border-slate-50 pb-3 mb-4">
                  <div className="flex items-center gap-1.5 text-xs text-slate-400 font-semibold">
                    <Calendar className="h-3.5 w-3.5" />
                    {formatDate(c.created_at)}
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 border rounded-full ${getStrengthClass(
                        c.strength
                      )}`}
                    >
                      {c.strength}
                    </span>
                    <button
                      onClick={(e) => handleDeleteCase(e, c._id)}
                      disabled={deletingId === c._id}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
                      title="Delete dispute case"
                    >
                      {deletingId === c._id ? (
                        <Loader2 className="h-4 w-4 animate-spin text-rose-600" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">INSURER</span>
                  <h3 className="font-bold text-slate-800 text-lg truncate group-hover:text-indigo-600 transition">
                    {c.insurer_name}
                  </h3>
                </div>

                <div className="mt-4 flex items-center justify-between bg-slate-50 border border-slate-100 p-3 rounded-xl">
                  <div>
                    <span className="text-[9px] font-bold text-slate-400 uppercase block leading-none mb-1">
                      DISPUTE SCORE
                    </span>
                    <span className="text-xl font-extrabold text-slate-900 leading-none">{c.dispute_score}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[9px] font-bold text-slate-400 uppercase block leading-none mb-1">
                      CITATIONS
                    </span>
                    <span className="text-xs font-bold text-slate-600 leading-none">
                      {c.citations.length} {c.citations.length === 1 ? "clause" : "clauses"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-50 flex items-center justify-between text-xs text-indigo-600 font-bold">
                <span>View Appeal Details</span>
                <ArrowUpRight className="h-4 w-4 transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
