"use client";

import React, { useRef, useState } from "react";
import { Upload, FileText, XCircle } from "lucide-react";

interface DocumentUploadProps {
  label: string;
  onFileSelect: (file: File | null) => void;
  selectedFile: File | null;
}

export default function DocumentUpload({ label, onFileSelect, selectedFile }: DocumentUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        onFileSelect(file);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0]);
    }
  };

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="space-y-2">
      <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider">
        {label}
      </label>
      
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-5 text-center cursor-pointer relative transition duration-200 min-h-[150px] flex flex-col justify-center items-center ${
          dragActive 
            ? "border-indigo-600 bg-indigo-50/20" 
            : selectedFile 
              ? "border-emerald-500 bg-emerald-50/10" 
              : "border-slate-200 bg-slate-50/50 hover:border-indigo-500 hover:bg-indigo-50/5"
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept=".pdf"
          onChange={handleChange}
          className="hidden"
        />

        {selectedFile ? (
          <div className="flex flex-col items-center space-y-2 w-full px-2">
            <FileText className="h-8 w-8 text-emerald-600 animate-bounce" />
            <p className="text-xs font-bold text-slate-800 truncate max-w-full">
              {selectedFile.name}
            </p>
            <button
              onClick={handleClear}
              className="text-xs text-rose-500 hover:text-rose-700 font-semibold flex items-center gap-1 mt-1 z-10"
            >
              <XCircle className="h-4 w-4" /> Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <Upload className="h-8 w-8 text-slate-400 mb-2" />
            <p className="text-xs font-bold text-slate-700">Drag &amp; drop PDF here</p>
            <p className="text-[10px] text-slate-400 mt-1">or click to browse files</p>
          </div>
        )}
      </div>
    </div>
  );
}
