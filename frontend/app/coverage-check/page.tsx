"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import { FileSearch, Upload, CheckCircle, XCircle, Loader2, AlertCircle, Percent, HelpCircle } from "lucide-react";

export default function CoverageCheckPage() {
  const router = useRouter();
  const [authLoading, setAuthLoading] = useState(true);
  
  // Form states
  const [file, setFile] = useState<File | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Results states
  const [result, setResult] = useState<{
    covered: boolean;
    confidence: number;
    relevant_clauses: string[];
    explanation: string;
  } | null>(null);

  // Authentication check
  useEffect(() => {
    supabase.auth.getSession().then((res: any) => {
      const session = res.data?.session;
      if (!session) {
        router.push("/auth/login");
      } else {
        setAuthLoading(false);
      }
    });
  }, [router]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF documents are supported.");
        setFile(null);
        return;
      }
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError("File is too large. Max size is 10MB.");
        setFile(null);
        return;
      }
      setError("");
      setFile(selectedFile);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !query.trim()) {
      setError("Please select a policy PDF and enter a query.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("policy_pdf", file);
    formData.append("query", query);

    try {
      // Send as multipart form
      const data = await api.post("/coverage/check", formData, false);
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to analyze coverage. Please verify backend configurations.");
    } finally {
      setLoading(false);
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
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Title Header */}
      <div className="mb-10 text-left">
        <h1 className="text-3xl font-extrabold text-slate-900 sm:text-4xl flex items-center gap-2">
          <FileSearch className="h-8 w-8 text-indigo-600" />
          Pre-Visit Coverage Check
        </h1>
        <p className="text-slate-600 mt-2 max-w-xl text-sm sm:text-base">
          Upload your health insurance policy and query whether a specific treatment, procedure, or drug is covered under your plan.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Upload Form Panel */}
        <form onSubmit={handleSubmit} className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 space-y-6">
          <h2 className="font-bold text-slate-800 text-lg">Check Coverage Policy</h2>
          
          {error && (
            <div className="bg-rose-50 border-l-4 border-rose-500 p-4 rounded text-sm text-rose-800 flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-rose-500 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Policy PDF Upload */}
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Insurance Policy PDF (max 10MB)
            </label>
            <div className="border-2 border-dashed border-slate-200 hover:border-indigo-500 rounded-2xl p-6 transition text-center cursor-pointer relative bg-slate-50/50 hover:bg-indigo-50/10">
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <Upload className="h-8 w-8 text-slate-500 mx-auto mb-2" />
              {file ? (
                <div>
                  <p className="text-sm font-bold text-indigo-600 truncate">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              ) : (
                <div>
                  <p className="text-sm font-semibold text-slate-700">Click to upload or drag &amp; drop</p>
                  <p className="text-xs text-slate-500 mt-1">PDF format only</p>
                </div>
              )}
            </div>
          </div>

          {/* Query input */}
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Coverage Question
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Is outpatient physical therapy covered? What is my deductible?"
              rows={3}
              required
              className="w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:bg-white focus:border-indigo-600 transition text-slate-900 text-sm resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !file || !query.trim()}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3.5 px-4 rounded-xl shadow-md transition flex items-center justify-center gap-2 disabled:opacity-75 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Analyzing Policy Clauses...
              </>
            ) : (
              "Check Coverage"
            )}
          </button>
        </form>

        {/* Results Panel */}
        <div className="space-y-6">
          {result ? (
            <div className="bg-white rounded-3xl p-6 shadow-xl border border-slate-100 space-y-6">
              {/* Coverage Decision Badge */}
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <span className="text-xs text-slate-500 font-bold block mb-1">COVERAGE STATUS</span>
                  {result.covered ? (
                    <span className="inline-flex items-center gap-1.5 text-emerald-800 bg-emerald-100 border border-emerald-200 px-3 py-1 rounded-full text-xs font-extrabold uppercase">
                      <CheckCircle className="h-4 w-4" /> Covered
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-rose-800 bg-rose-100 border border-rose-200 px-3 py-1 rounded-full text-xs font-extrabold uppercase">
                      <XCircle className="h-4 w-4" /> Not Covered
                    </span>
                  )}
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-500 font-bold block mb-1">CONFIDENCE</span>
                  <span className="inline-flex items-center gap-1 text-slate-800 bg-slate-100 border border-slate-200 px-3 py-1 rounded-full text-xs font-extrabold">
                    <Percent className="h-3.5 w-3.5" /> {(result.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Explanatory Paragraph */}
              <div className="space-y-2">
                <h3 className="font-bold text-slate-800 text-sm flex items-center gap-1.5">
                  <HelpCircle className="h-4 w-4 text-indigo-500" /> Analyst Explanation
                </h3>
                <p className="text-slate-700 text-sm leading-relaxed whitespace-pre-line font-medium">
                  {result.explanation}
                </p>
              </div>

              {/* Relevant Clauses */}
              {result.relevant_clauses.length > 0 && (
                <div className="space-y-3 pt-4 border-t border-slate-100">
                  <h3 className="font-bold text-slate-800 text-sm">Relevant Policy Excerpts</h3>
                  <div className="space-y-2.5">
                    {result.relevant_clauses.map((clause, idx) => (
                      <div key={idx} className="bg-slate-50 p-3 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed font-mono">
                        &quot;{clause}&quot;
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-slate-100/50 rounded-3xl p-8 border-2 border-dashed border-slate-300 flex flex-col items-center justify-center text-center h-[380px]">
              <FileSearch className="h-12 w-12 text-slate-400 mb-3" />
              <h3 className="font-bold text-slate-700 mb-1">Waiting for Analysis</h3>
              <p className="text-slate-500 text-xs max-w-[240px]">
                Upload your insurance policy PDF and enter your question to see coverage results.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
