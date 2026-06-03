import React from "react";
import TriageChat from "@/components/TriageChat";
import { Stethoscope } from "lucide-react";

export const metadata = {
  title: "Symptom Triage — ClaimSure",
  description: "Assess symptoms and identify recommended healthcare actions with ClaimSure Triage.",
};

export default function TriagePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Title Header */}
      <div className="mb-10 text-left">
        <h1 className="text-3xl font-extrabold text-slate-900 sm:text-4xl flex items-center gap-2">
          <Stethoscope className="h-8 w-8 text-indigo-600" />
          Symptom Triage Assistant
        </h1>
        <p className="text-slate-600 mt-2 max-w-xl text-sm sm:text-base">
          Describe your symptoms, and our clinical model will suggest appropriate specialist recommendations, medical checklists, and clinical urgency evaluations.
        </p>
      </div>

      {/* Chat Component */}
      <TriageChat />
    </div>
  );
}
