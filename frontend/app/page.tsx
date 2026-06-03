import React from "react";
import Link from "next/link";
import { Stethoscope, FileSearch, Scale, ShieldCheck, ArrowRight, Activity, CheckCircle, FileText } from "lucide-react";

export default function Home() {
  return (
    <div className="relative overflow-hidden bg-slate-50">
      {/* Background Graphic Accents */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[600px] pointer-events-none overflow-hidden -z-10">
        <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-indigo-200/20 rounded-full blur-3xl" />
        <div className="absolute top-[20%] right-[10%] w-[400px] h-[400px] bg-emerald-200/10 rounded-full blur-3xl" />
      </div>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 text-center lg:pt-32">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-xs font-semibold text-indigo-700 mb-6 animate-pulse">
          <Activity className="h-4 w-4" /> Powered by LangGraph & Groq AI
        </div>
        <h1 className="mx-auto max-w-4xl text-5xl font-extrabold tracking-tight text-slate-900 sm:text-6xl md:text-7xl lg:leading-[1.15]">
          Take Control of Your{" "}
          <span className="bg-gradient-to-r from-blue-900 via-indigo-900 to-indigo-950 bg-clip-text text-transparent">
            Medical Bills
          </span>{" "}
          &amp;{" "}
          <span className="bg-gradient-to-r from-emerald-600 to-teal-500 bg-clip-text text-transparent">
            Insurance Claims
          </span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-700 sm:text-xl font-medium">
          ClaimSure uses advanced artificial intelligence to validate claims, review coverage clauses, and automatically draft appeals. Stop letting wrongful claim denials cost you.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Link
            href="/dispute"
            className="flex items-center gap-2 bg-gradient-to-br from-[#4F46E5] to-[#7C3AED] hover:from-[#4338CA] hover:to-[#6D28D9] text-white font-bold px-8 py-4 rounded-2xl shadow-[0_10px_25px_rgba(79,70,229,0.25)] hover:shadow-[0_12px_30px_rgba(79,70,229,0.35)] transition duration-200 transform hover:-translate-y-0.5 group"
          >
            Start Claim Appeal
            <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition" />
          </Link>
          <Link
            href="/triage"
            className="flex items-center gap-2 bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 font-bold px-8 py-4 rounded-2xl shadow-md transition duration-200 transform hover:-translate-y-0.5"
          >
            Check Symptoms
          </Link>
        </div>

        {/* Feature Icons Grid */}
        <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1 */}
          <div className="bg-white rounded-3xl p-8 shadow-xl border border-slate-100/80 hover:shadow-2xl hover:border-indigo-100 transition duration-300 flex flex-col text-left group">
            <div className="bg-indigo-50 p-4 rounded-2xl w-fit text-indigo-600 mb-6 group-hover:scale-110 transition duration-300">
              <Stethoscope className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">1. Healthcare Triage</h3>
            <p className="text-slate-700 text-sm leading-relaxed mb-4">
              Enter your symptoms to receive an immediate recommendation for medical specialists, checklist guidelines, and urgency level warnings.
            </p>
            <Link href="/triage" className="text-indigo-600 font-bold text-sm mt-auto inline-flex items-center gap-1 group-hover:underline">
              Check Symptoms <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Card 2 */}
          <div className="bg-white rounded-3xl p-8 shadow-xl border border-slate-100/80 hover:shadow-2xl hover:border-indigo-100 transition duration-300 flex flex-col text-left group">
            <div className="bg-emerald-50 p-4 rounded-2xl w-fit text-emerald-600 mb-6 group-hover:scale-110 transition duration-300">
              <FileSearch className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">2. Pre-Visit Policy Check</h3>
            <p className="text-slate-700 text-sm leading-relaxed mb-4">
              Upload your insurance policy and ask questions about procedure coverage. Our semantic check validates clauses automatically.
            </p>
            <Link href="/coverage-check" className="text-emerald-600 font-bold text-sm mt-auto inline-flex items-center gap-1 group-hover:underline">
              Verify Policy <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Card 3 */}
          <div className="bg-white rounded-3xl p-8 shadow-xl border border-slate-100/80 hover:shadow-2xl hover:border-indigo-100 transition duration-300 flex flex-col text-left group">
            <div className="bg-blue-50 p-4 rounded-2xl w-fit text-blue-600 mb-6 group-hover:scale-110 transition duration-300">
              <Scale className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">3. Claim Dispute Resolver</h3>
            <p className="text-slate-700 text-sm leading-relaxed mb-4">
              Upload your policy, medical bill, and doctor&apos;s report. The LangGraph agent cross-references findings to build structured dispute arguments.
            </p>
            <Link href="/dispute" className="text-blue-600 font-bold text-sm mt-auto inline-flex items-center gap-1 group-hover:underline">
              Resolve Denial <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Trust Stats / Features */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white py-16 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          <div className="flex flex-col items-center">
            <ShieldCheck className="h-10 w-10 text-emerald-400 mb-4" />
            <h4 className="text-3xl font-extrabold">100% Secure</h4>
            <p className="text-slate-200 text-sm mt-1">GDPR compliant secure document parser</p>
          </div>
          <div className="flex flex-col items-center">
            <FileText className="h-10 w-10 text-emerald-400 mb-4" />
            <h4 className="text-3xl font-extrabold">Instant Audits</h4>
            <p className="text-slate-200 text-sm mt-1">Claim cross-referencing in 3-10 seconds</p>
          </div>
          <div className="flex flex-col items-center">
            <CheckCircle className="h-10 w-10 text-emerald-400 mb-4" />
            <h4 className="text-3xl font-extrabold">95%+ Accuracy</h4>
            <p className="text-slate-200 text-sm mt-1">Cites exact page numbers and clauses</p>
          </div>
        </div>
      </div>
    </div>
  );
}
