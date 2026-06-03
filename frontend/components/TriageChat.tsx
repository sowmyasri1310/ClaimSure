"use client";

import React, { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import { Stethoscope, Send, User, Bot, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";

interface Message {
  id: string;
  sender: "user" | "bot";
  text: string;
  triageData?: {
    specialist: string;
    urgency: "low" | "medium" | "high";
    reasoning: string;
    pre_visit_checklist: string[];
  };
}

export default function TriageChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "bot",
      text: "Hello! I am your AI Medical Triage Assistant. Please enter your age, any existing conditions, and list your symptoms so I can recommend a specialist and suggest the urgency level."
    }
  ]);
  const [symptoms, setSymptoms] = useState("");
  const [age, setAge] = useState<number | "">("");
  const [existingConditions, setExistingConditions] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symptoms.trim() || age === "") return;

    const userMsgId = `user-${Date.now()}`;
    const userMsg: Message = {
      id: userMsgId,
      sender: "user",
      text: `Symptoms: ${symptoms}\nAge: ${age}\nExisting Conditions: ${existingConditions || "None"}`
    };

    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError("");

    try {
      const result = await api.post("/triage/analyze", {
        symptoms,
        age: Number(age),
        existing_conditions: existingConditions || "None"
      });

      const botMsgId = `bot-${Date.now()}`;
      const botMsg: Message = {
        id: botMsgId,
        sender: "bot",
        text: result.specialist === "N/A"
          ? result.reasoning
          : `Based on your analysis, I recommend seeing a **${result.specialist}**.`,
        triageData: result.specialist === "N/A" ? undefined : {
          specialist: result.specialist,
          urgency: result.urgency as "low" | "medium" | "high",
          reasoning: result.reasoning,
          pre_visit_checklist: result.pre_visit_checklist || []
        }
      };

      setMessages((prev) => [...prev, botMsg]);
      // Reset only symptoms
      setSymptoms("");
    } catch (err: any) {
      setError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const getUrgencyBadge = (urgency: "low" | "medium" | "high") => {
    switch (urgency) {
      case "high":
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "medium":
        return "bg-amber-100 text-amber-800 border-amber-200";
      case "low":
      default:
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
    }
  };

  return (
    <div className="flex flex-col lg:flex-row gap-8 max-w-6xl mx-auto">
      {/* Sidebar: User Details */}
      <div className="w-full lg:w-80 bg-white rounded-3xl p-6 shadow-xl border border-slate-100 h-fit space-y-5">
        <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
          <div className="bg-indigo-50 p-2 rounded-xl text-indigo-600">
            <Stethoscope className="h-5 w-5" />
          </div>
          <h2 className="font-bold text-slate-800 text-lg">Triage Parameters</h2>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">
              Age (Years)
            </label>
            <input
              type="number"
              value={age}
              onChange={(e) => setAge(e.target.value === "" ? "" : Number(e.target.value))}
              placeholder="e.g. 35"
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-indigo-600 transition text-slate-900 text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5">
              Existing Conditions
            </label>
            <textarea
              value={existingConditions}
              onChange={(e) => setExistingConditions(e.target.value)}
              placeholder="e.g. Diabetes, Hypertension, Asthma"
              rows={3}
              className="w-full px-4 py-2.5 bg-slate-50 border border-slate-300 rounded-xl outline-none focus:border-indigo-600 transition text-slate-900 text-sm resize-none"
            />
          </div>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-grow bg-white rounded-3xl shadow-xl border border-slate-100 flex flex-col overflow-hidden h-[600px]">
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-blue-900 to-indigo-950 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-white/10 p-2 rounded-lg">
              <Bot className="h-5 w-5 text-emerald-400 animate-pulse" />
            </div>
            <div>
              <h3 className="font-bold text-sm">ClaimSure Triage Assistant</h3>
              <p className="text-xs text-slate-300">Evaluating symptoms &amp; recommending care</p>
            </div>
          </div>
        </div>

        {/* Chat Feed */}
        <div className="flex-grow p-6 overflow-y-auto space-y-6 bg-slate-50/50">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-[80%] ${msg.sender === "user" ? "ml-auto flex-row-reverse" : "mr-auto"}`}
            >
              {/* Avatar Icon */}
              <div
                className={`flex-shrink-0 h-9 w-9 rounded-full flex items-center justify-center ${
                  msg.sender === "user" ? "bg-indigo-600 text-white" : "bg-slate-200 text-slate-700"
                }`}
              >
                {msg.sender === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>

              {/* Message Bubble */}
              <div className="space-y-3">
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed ${
                    msg.sender === "user"
                      ? "bg-indigo-600 text-white rounded-tr-none shadow-md"
                      : "bg-white text-slate-800 rounded-tl-none border border-slate-200 shadow-sm"
                  }`}
                >
                  <p className="whitespace-pre-line">{msg.text}</p>
                </div>

                {/* Structured Triage Data */}
                {msg.triageData && (
                  <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 max-w-md">
                    {/* Urgency and Specialist */}
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                      <div>
                        <span className="text-xs text-slate-500 font-bold block">RECOMMENDED CARE</span>
                        <span className="font-bold text-slate-900 text-base">{msg.triageData.specialist}</span>
                      </div>
                      <span
                        className={`text-xs font-extrabold uppercase px-3 py-1 border rounded-full ${getUrgencyBadge(
                          msg.triageData.urgency
                        )}`}
                      >
                        {msg.triageData.urgency} Urgency
                      </span>
                    </div>

                    {/* Reasoning */}
                    <div className="space-y-1">
                      <span className="text-xs text-slate-500 font-bold flex items-center gap-1">
                        <AlertTriangle className="h-3.5 w-3.5 text-indigo-500" /> CLINICAL EXPLANATION
                      </span>
                      <p className="text-slate-600 text-sm leading-relaxed">{msg.triageData.reasoning}</p>
                    </div>

                    {/* Checklist */}
                    {msg.triageData.pre_visit_checklist.length > 0 && (
                      <div className="space-y-2 pt-2 border-t border-slate-100">
                        <span className="text-xs text-slate-500 font-bold flex items-center gap-1">
                          <CheckCircle className="h-3.5 w-3.5 text-emerald-500" /> PRE-VISIT CHECKLIST
                        </span>
                        <ul className="space-y-1.5 pl-1.5">
                          {msg.triageData.pre_visit_checklist.map((item, idx) => (
                            <li key={idx} className="text-xs text-slate-600 flex items-start gap-2">
                              <span className="text-emerald-500 font-bold mt-0.5">•</span>
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Loading bubble */}
          {loading && (
            <div className="flex gap-3 max-w-[80%] mr-auto">
              <div className="flex-shrink-0 h-9 w-9 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center">
                <Bot className="h-4 w-4" />
              </div>
              <div className="bg-white border border-slate-200 p-4 rounded-2xl rounded-tl-none shadow-sm flex items-center gap-2 text-slate-500 text-sm">
                <Loader2 className="h-4 w-4 animate-spin text-indigo-600" />
                Analyzing symptoms and medical history...
              </div>
            </div>
          )}

          {error && (
            <div className="bg-rose-50 border-l-4 border-rose-500 p-4 rounded-xl text-sm text-rose-800 max-w-[80%] mr-auto">
              {error}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="bg-white p-4 border-t border-slate-200 flex gap-3 items-center">
          <input
            type="text"
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
            disabled={age === ""}
            placeholder={
              age === ""
                ? "Please enter your age in the sidebar first..."
                : "Type in details about your current symptoms..."
            }
            className="flex-grow px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-indigo-600 transition text-slate-900 text-sm disabled:opacity-75 disabled:cursor-not-allowed"
            required
          />
          <button
            type="submit"
            disabled={!symptoms.trim() || loading || age === ""}
            className="bg-indigo-600 hover:bg-indigo-700 text-white p-3 rounded-xl shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-5 w-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
