"use client";

import React from "react";
import { CheckCircle2, Loader2, Circle, AlertCircle } from "lucide-react";
import type { ProgressStepItem } from "@/types/investigation";

interface InvestigationProgressProps {
  steps: ProgressStepItem[];
  isInvestigating: boolean;
}

export function InvestigationProgress({
  steps,
  isInvestigating,
}: InvestigationProgressProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
          Investigation Status
        </h2>
        {isInvestigating ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-sky-500/10 px-2.5 py-0.5 text-xs font-medium text-sky-400 ring-1 ring-sky-500/20">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sky-400" />
            Live (InsForge Realtime)
          </span>
        ) : (
          <span className="text-xs text-slate-500">Realtime Stream Ready</span>
        )}
      </div>

      <div className="mt-5 space-y-3">
        {steps.map((step) => {
          const isDone = step.status === "completed";
          const isRunning = step.status === "running";
          const isErr = step.status === "error";

          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                isDone
                  ? "bg-emerald-950/20 text-emerald-300 font-medium"
                  : isRunning
                  ? "bg-sky-950/30 text-sky-300 font-medium ring-1 ring-sky-500/30"
                  : isErr
                  ? "bg-rose-950/20 text-rose-300"
                  : "text-slate-500"
              }`}
            >
              <div className="shrink-0">
                {isDone && <CheckCircle2 className="h-4 w-4 text-emerald-400" />}
                {isRunning && <Loader2 className="h-4 w-4 animate-spin text-sky-400" />}
                {isErr && <AlertCircle className="h-4 w-4 text-rose-400" />}
                {!isDone && !isRunning && !isErr && (
                  <Circle className="h-4 w-4 text-slate-600" />
                )}
              </div>
              <span className="flex-1">{step.label}</span>
              {isDone && (
                <span className="text-xs text-emerald-400/80 font-mono">Done</span>
              )}
              {isRunning && (
                <span className="text-xs text-sky-400/80 font-mono animate-pulse">Running</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
