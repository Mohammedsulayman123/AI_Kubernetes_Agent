"use client";

import React, { useEffect, useState } from "react";
import {
  FlaskConical,
  ChevronDown,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Play,
} from "lucide-react";
import {
  getScenarios,
  applyScenario,
  cleanupScenario,
  type ScenarioInfo,
} from "@/services/clusters";

interface TestScenariosProps {
  selectedContext: string | null;
  onScenarioApplied: (namespace: string, podName: string | null) => void; // callback to target the scenario namespace
}

export function TestScenarios({ selectedContext, onScenarioApplied }: TestScenariosProps) {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [open, setOpen] = useState(false);
  const [applying, setApplying] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState<string | null>(null);
  const [result, setResult] = useState<{
    type: "success" | "error";
    message: string;
    scenarioId: string;
  } | null>(null);

  useEffect(() => {
    getScenarios().then(setScenarios);
  }, []);

  const handleApply = async (s: ScenarioInfo) => {
    setApplying(s.id);
    setResult(null);
    const res = await applyScenario(s.id, selectedContext);
    setApplying(null);

    if (res.success) {
      setResult({
        type: "success",
        message: `✓ ${res.title ?? s.title} is ready. Investigating its isolated namespace…`,
        scenarioId: s.id,
      });
      setOpen(false);
      setTimeout(() => {
        onScenarioApplied(res.namespace ?? s.namespace, null);
        setResult(null);
      }, 250);
    } else {
      setResult({
        type: "error",
        message: res.error ?? "Failed to apply scenario.",
        scenarioId: s.id,
      });
    }
  };

  const handleCleanup = async (s: ScenarioInfo) => {
    setCleaning(s.id);
    setResult(null);
    const res = await cleanupScenario(s.id, selectedContext);
    setCleaning(null);
    setResult({
      type: res.success ? "success" : "error",
      message: res.success
        ? `✓ ${s.title} resources removed.`
        : res.error ?? "Cleanup failed.",
      scenarioId: s.id,
    });
  };

  if (scenarios.length === 0) return null;

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/60 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-amber-500/40 hover:text-amber-300"
      >
        <FlaskConical className="h-4 w-4" />
        <span>Test Scenarios</span>
        <ChevronDown
          className={`h-3.5 w-3.5 text-slate-500 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Result banner */}
      {result && (
        <div
          className={`mt-3 flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm ${
            result.type === "success"
              ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
              : "border-rose-500/30 bg-rose-950/20 text-rose-300"
          }`}
        >
          {result.type === "success" ? (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          ) : (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
          )}
          <p className="whitespace-pre-line text-xs leading-relaxed">{result.message}</p>
        </div>
      )}

      {/* Dropdown */}
      {open && (
        <div className="absolute left-0 z-50 mt-2 w-96 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/50 overflow-hidden">
          <div className="border-b border-slate-800 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Inject Failure Scenario
            </p>
            <p className="mt-0.5 text-xs text-slate-500">
              Applies a broken workload to the selected cluster. AI will diagnose it.
            </p>
          </div>

          <div className="divide-y divide-slate-800 max-h-80 overflow-y-auto">
            {scenarios.map((s) => (
              <div key={s.id} className="px-4 py-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-200 leading-snug">
                      {s.title}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500 leading-relaxed">
                      {s.description}
                    </p>
                  </div>
                </div>
                <div className="mt-2.5 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleApply(s)}
                    disabled={applying !== null || cleaning !== null}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-sky-500/10 px-3 py-1.5 text-xs font-medium text-sky-300 hover:bg-sky-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    {applying === s.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Play className="h-3 w-3 fill-current" />
                    )}
                    {applying === s.id ? "Applying…" : "Apply"}
                  </button>
                  <button
                    type="button"
                    onClick={() => handleCleanup(s)}
                    disabled={applying !== null || cleaning !== null}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-400 hover:bg-slate-700 hover:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    {cleaning === s.id ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Trash2 className="h-3 w-3" />
                    )}
                    {cleaning === s.id ? "Cleaning…" : "Cleanup"}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Backdrop */}
      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
      )}
    </div>
  );
}
