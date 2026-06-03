"use client";

import React, { useState } from "react";
import { Copy, Check, FileCheck, FileText } from "lucide-react";

interface DisputeLetterProps {
  letterText: string;
}

export default function DisputeLetter({ letterText }: DisputeLetterProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (letterText) {
      navigator.clipboard.writeText(letterText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-hidden flex flex-col">
      {/* Header controls */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-950 px-6 py-4 flex items-center justify-between text-white">
        <div className="flex items-center gap-2">
          <FileCheck className="h-5 w-5 text-emerald-400" />
          <h3 className="font-bold text-sm">Dispute Appeal Letter</h3>
        </div>
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
              <Copy className="h-3.5 w-3.5" /> Copy to Clipboard
            </>
          )}
        </button>
      </div>

      {/* Editor Content Area */}
      <div className="p-6 bg-slate-50/50 font-mono text-xs text-slate-700 leading-relaxed whitespace-pre-wrap max-h-[450px] overflow-y-auto border-b border-slate-100">
        {letterText || "No letter content generated."}
      </div>

      {/* Mandatory Disclaimer warnings */}
      <div className="bg-amber-50 p-4 border-l-4 border-amber-500 text-xs text-amber-900 leading-relaxed">
        <strong>Disclaimer:</strong> This letter was generated with AI assistance and should be reviewed and verified by the patient before submission.
      </div>
    </div>
  );
}
