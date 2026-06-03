"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Link from "next/link";
import { ShieldCheck, Mail, Lock, Loader2, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (authError) throw authError;

      // Force dispatch session change and redirect
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("storage"));
      }
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Invalid email or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden">
        {/* Header Branding */}
        <div className="bg-gradient-to-r from-blue-900 to-indigo-950 p-8 text-center text-white relative">
          <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-2xl -mr-8 -mt-8" />
          <div className="flex justify-center mb-3">
            <div className="bg-white/10 p-3 rounded-xl backdrop-blur-md">
              <ShieldCheck className="h-8 w-8 text-emerald-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome to ClaimSure</h1>
          <p className="text-slate-300 text-sm mt-1">
            Access your medical claim dispute resolver
          </p>
        </div>

        {/* Form Body */}
        <form onSubmit={handleLogin} className="p-8 space-y-6">
          {error && (
            <div className="bg-rose-50 border-l-4 border-rose-500 p-4 rounded text-sm text-rose-800">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 h-5 w-5" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="w-full pl-11 pr-4 py-3 border border-slate-200 rounded-xl outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition text-slate-900"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 h-5 w-5" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-4 py-3 border border-slate-200 rounded-xl outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition text-slate-900"
                />
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-xl shadow-md transition flex items-center justify-center gap-2 group disabled:opacity-75 disabled:cursor-not-allowed"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <>
                Sign In <ArrowRight className="h-5 w-5 group-hover:translate-x-0.5 transition" />
              </>
            )}
          </button>

          <p className="text-center text-sm text-slate-600">
            Don&apos;t have an account?{" "}
            <Link
              href="/auth/signup"
              className="text-indigo-600 hover:text-indigo-700 font-semibold underline underline-offset-4"
            >
              Sign up
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
