"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import { Scale, Upload, AlertCircle, Loader2, ArrowRight, FileText } from "lucide-react";

export default function DisputeUploadPage() {
  const router = useRouter();
  const [authLoading, setAuthLoading] = useState(true);

  // Form inputs
  const [userName, setUserName] = useState("");
  const [insurerName, setInsurerName] = useState("");
  const [policyFile, setPolicyFile] = useState<File | null>(null);
  const [billFile, setBillFile] = useState<File | null>(null);
  const [reportFile, setReportFile] = useState<File | null>(null);

  // Status states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Route auth protection
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

  const validateFile = (file: File): string | null => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      return "Only PDF documents are allowed.";
    }
    if (file.size > 10 * 1024 * 1024) {
      return "Maximum file size allowed is 10MB.";
    }
    return null;
  };

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    setter: React.Dispatch<React.SetStateAction<File | null>>
  ) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      const err = validateFile(selected);
      if (err) {
        setError(err);
        setter(null);
        return;
      }
      setError("");
      setter(selected);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!userName.trim() || !insurerName.trim() || !policyFile || !billFile || !reportFile) {
      setError("Please fill out all fields and upload all three required documents.");
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("policy_pdf", policyFile);
    formData.append("bill_pdf", billFile);
    formData.append("report_pdf", reportFile);
    formData.append("user_name", userName);
    formData.append("insurer_name", insurerName);

    try {
      const data = await api.post("/dispute/analyze", formData, false);
      
      // Store result in local storage for the result route
      if (typeof window !== "undefined") {
        localStorage.setItem("claimsure_dispute_result", JSON.stringify(data));
      }
      
      router.push("/dispute/result");
    } catch (err: any) {
      setError(err.message || "Claims analysis agent failed. Please verify API configurations.");
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
          <Scale className="h-8 w-8 text-indigo-600" />
          Claim Dispute Resolver
        </h1>
        <p className="text-slate-600 mt-2 max-w-xl text-sm sm:text-base">
          Resolve claim rejections by uploading your Policy, hospital Bill, and doctor&apos;s medical Report. Our multi-agent LangGraph flow will discover mismatches and output a formal appeal letter.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-3xl p-8 shadow-xl border border-slate-100 space-y-8">
        <h2 className="font-bold text-slate-800 text-xl">Upload Claim Documents</h2>

        {error && (
          <div className="bg-rose-50 border-l-4 border-rose-500 p-4 rounded-xl text-sm text-rose-800 flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-rose-500 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Text Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Patient Full Name
            </label>
            <input
              type="text"
              required
              value={userName}
              onChange={(e) => setUserName(e.target.value)}
              placeholder="e.g. John Doe"
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-indigo-600 transition text-slate-900 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
              Insurance Provider Name
            </label>
            <input
              type="text"
              required
              value={insurerName}
              onChange={(e) => setInsurerName(e.target.value)}
              placeholder="e.g. Blue Cross"
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-indigo-600 transition text-slate-900 text-sm"
            />
          </div>
        </div>

        {/* Triple PDF Upload Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Doc 1: Policy */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
              1. Insurance Policy PDF
            </label>
            <div className="border border-dashed border-slate-200 hover:border-indigo-500 rounded-2xl p-5 text-center cursor-pointer relative bg-slate-50/50 hover:bg-indigo-50/10 min-h-[160px] flex flex-col justify-center items-center">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileChange(e, setPolicyFile)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              {policyFile ? (
                <div className="flex flex-col items-center">
                  <FileText className="h-7 w-7 text-indigo-600 mb-1" />
                  <p className="text-xs font-bold text-slate-800 line-clamp-2">{policyFile.name}</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <Upload className="h-7 w-7 text-slate-400 mb-1" />
                  <p className="text-xs font-bold text-slate-700">Policy PDF</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">Max size 10MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Doc 2: Hospital Bill */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
              2. Hospital Bill PDF
            </label>
            <div className="border border-dashed border-slate-200 hover:border-indigo-500 rounded-2xl p-5 text-center cursor-pointer relative bg-slate-50/50 hover:bg-indigo-50/10 min-h-[160px] flex flex-col justify-center items-center">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileChange(e, setBillFile)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              {billFile ? (
                <div className="flex flex-col items-center">
                  <FileText className="h-7 w-7 text-indigo-600 mb-1" />
                  <p className="text-xs font-bold text-slate-800 line-clamp-2">{billFile.name}</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <Upload className="h-7 w-7 text-slate-400 mb-1" />
                  <p className="text-xs font-bold text-slate-700">Hospital Bill PDF</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">Max size 10MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Doc 3: Doctor Report */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
              3. Doctor&apos;s Report PDF
            </label>
            <div className="border border-dashed border-slate-200 hover:border-indigo-500 rounded-2xl p-5 text-center cursor-pointer relative bg-slate-50/50 hover:bg-indigo-50/10 min-h-[160px] flex flex-col justify-center items-center">
              <input
                type="file"
                accept=".pdf"
                onChange={(e) => handleFileChange(e, setReportFile)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              {reportFile ? (
                <div className="flex flex-col items-center">
                  <FileText className="h-7 w-7 text-indigo-600 mb-1" />
                  <p className="text-xs font-bold text-slate-800 line-clamp-2">{reportFile.name}</p>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <Upload className="h-7 w-7 text-slate-400 mb-1" />
                  <p className="text-xs font-bold text-slate-700">Doctor Report PDF</p>
                  <p className="text-[10px] text-slate-400 mt-0.5">Max size 10MB</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !policyFile || !billFile || !reportFile || !userName.trim() || !insurerName.trim()}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-4 rounded-xl shadow-lg hover:shadow-xl transition flex items-center justify-center gap-2 group disabled:opacity-75 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin text-white" />
              LangGraph Agent executing claims analysis (takes 5-10s)...
            </>
          ) : (
            <>
              Analyze Claim &amp; Generate Appeal{" "}
              <ArrowRight className="h-5 w-5 group-hover:translate-x-0.5 transition" />
            </>
          )}
        </button>
      </form>
    </div>
  );
}
