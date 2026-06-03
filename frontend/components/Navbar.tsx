"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { ShieldAlert, LogOut, Menu, X, User, LayoutDashboard, Stethoscope, FileSearch, Scale } from "lucide-react";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Check session on mount
    supabase.auth.getSession().then((res: any) => {
      setUser(res.data?.session?.user ?? null);
    });

    // Listen to changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event: any, session: any) => {
      setUser(session?.user ?? null);
    });

    // Force periodic re-check (handles local storage dispatch events)
    const handleStorageChange = () => {
      supabase.auth.getSession().then((res: any) => {
        setUser(res.data?.session?.user ?? null);
      });
    };
    window.addEventListener("storage", handleStorageChange);

    return () => {
      subscription.unsubscribe();
      window.removeEventListener("storage", handleStorageChange);
    };
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    // Dispatch session clear event
    window.dispatchEvent(new Event("storage"));
    router.push("/auth/login");
    setIsOpen(false);
  };

  const navLinks = [
    { name: "Symptom Triage", href: "/triage", icon: Stethoscope },
    { name: "Coverage Check", href: "/coverage-check", icon: FileSearch, protected: true },
    { name: "Dispute Claim", href: "/dispute", icon: Scale, protected: true },
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard, protected: true },
  ];

  const activeLinkClass = "text-indigo-700 bg-indigo-50 border-indigo-600 font-bold";
  const inactiveLinkClass = "text-slate-700 hover:text-indigo-600 hover:bg-slate-50 border-transparent";

  return (
    <nav className="bg-white border-b border-slate-100 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 mr-8 group">
              <div className="bg-gradient-to-br from-indigo-600 to-indigo-900 p-2 rounded-xl text-white shadow-md shadow-indigo-100 group-hover:scale-105 transition duration-200">
                <ShieldAlert className="h-5 w-5 text-teal-400" />
              </div>
              <span className="text-xl font-extrabold tracking-tight flex items-center">
                <span className="text-[#3B5CCC]">Claim</span>
                <span className="text-[#14B8A6]">Sure</span>
              </span>
            </Link>

            {/* Desktop Navigation Links */}
            <div className="hidden md:flex space-x-1">
              {navLinks.map((link) => {
                // If it is protected and user is not logged in, hide it in the main navigation
                if (link.protected && !user) return null;
                const isActive = pathname === link.href || pathname.startsWith(link.href + "/");
                const Icon = link.icon;

                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-semibold border-b-2 transition ${
                      isActive ? activeLinkClass : inactiveLinkClass
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {link.name}
                  </Link>
                );
              })}
            </div>
          </div>

          {/* Desktop Right Panel (User Session Info / Login Buttons) */}
          <div className="hidden md:flex items-center gap-4">
            {user ? (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 py-1.5 px-3 rounded-full text-xs font-semibold text-slate-700">
                  <User className="h-3.5 w-3.5 text-slate-500" />
                  <span className="max-w-[120px] truncate">{user.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 text-xs text-rose-600 hover:bg-rose-50 border border-rose-100 hover:border-rose-200 py-1.5 px-3 rounded-full transition font-semibold"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Logout
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/auth/login"
                  className="text-indigo-600 hover:text-indigo-700 hover:bg-slate-50 px-4 py-2 rounded-xl text-sm font-semibold transition"
                >
                  Login
                </Link>
                <Link
                  href="/auth/signup"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-semibold shadow transition"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>

          {/* Mobile hamburger menu */}
          <div className="flex items-center md:hidden">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="inline-flex items-center justify-center p-2 rounded-xl text-slate-600 hover:bg-slate-100 focus:outline-none transition"
            >
              {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Panel */}
      {isOpen && (
        <div className="md:hidden bg-white border-t border-slate-50 py-3 px-4 space-y-2 shadow-inner">
          {navLinks.map((link) => {
            if (link.protected && !user) return null;
            const isActive = pathname === link.href || pathname.startsWith(link.href + "/");
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${
                  isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-700 hover:bg-slate-50"
                }`}
              >
                <Icon className="h-5 w-5" />
                {link.name}
              </Link>
            );
          })}

          <hr className="my-2 border-slate-100" />

          {user ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 p-3 rounded-xl text-xs text-slate-700">
                <User className="h-4 w-4 text-slate-500" />
                <span className="truncate">{user.email}</span>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 text-rose-600 bg-rose-50 hover:bg-rose-100 p-3 rounded-xl text-sm font-bold transition"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2 pt-2">
              <Link
                href="/auth/login"
                onClick={() => setIsOpen(false)}
                className="text-center text-indigo-600 bg-indigo-50 border border-indigo-100 p-3 rounded-xl text-sm font-bold transition animate-fade-in"
              >
                Login
              </Link>
              <Link
                href="/auth/signup"
                onClick={() => setIsOpen(false)}
                className="text-center text-white bg-indigo-600 hover:bg-indigo-700 p-3 rounded-xl text-sm font-bold shadow transition"
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
