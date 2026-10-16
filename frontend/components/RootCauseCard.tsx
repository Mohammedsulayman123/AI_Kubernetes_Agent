"use client";

import React, { useState } from "react";
import { Check, Copy, Terminal, Zap, ShieldAlert, Sparkles, Heart, Loader2 } from "lucide-react";
import type { Diagnosis } from "@/types/investigation";

interface RootCauseCardProps {
  diagnosis: Diagnosis | null;
  clusterHealthy?: boolean | null;
  isInvestigating?: boolean;
}

export function RootCauseCard({ diagnosis, clusterHealthy, isInvestigating }: RootCauseCardProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Investigating — show spinner skeleton
  if (isInvestigating && !diagnosis) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-sky-800/50 bg-sky-950/10 p-10 text-center gap-4">
        <Loader2 className="h-8 w-8 text-sky-500 animate-spin" />
        <div>
          <h3 className="text-sm font-semibold text-sky-300">Investigating Kubernetes Cluster…</h3>
          <p className="mt-1 text-xs text-slate-500">
            Collecting evidence from pods, logs, events, deployments and networking.
          </p>
        </div>
      </div>
    );
  }

  // Healthy cluster
  if (clusterHealthy && !diagnosis) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-emerald-800/30 bg-emerald-950/10 p-10 text-center gap-4">
        <Heart className="h-8 w-8 text-emerald-400" />
        <div>
          <h3 className="text-sm font-semibold text-emerald-300">
            No Critical Issues Detected
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            Cluster appears healthy. All pods, events, and networking look good.
          </p>
        </div>
      </div>
    );
  }

  // No diagnosis yet
  if (!diagnosis) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30 p-10 text-center">
        <Sparkles className="h-8 w-8 text-slate-600 mb-3" />
        <h3 className="text-sm font-medium text-slate-300">No Diagnosis Available Yet</h3>
        <p className="mt-1 max-w-sm text-xs text-slate-500">
          Click &ldquo;Investigate Cluster&rdquo; above to run evidence collection and Senior SRE AI reasoning.
        </p>
      </div>
    );
  }


  const handleCopy = (cmd: string, index: number) => {
    navigator.clipboard.writeText(cmd);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const primaryCommand =
    diagnosis.kubectl_commands && diagnosis.kubectl_commands.length > 0
      ? diagnosis.kubectl_commands[0]
      : "";

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-6 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-amber-400" />
          <h2 className="text-base font-semibold tracking-tight text-slate-100">
            Diagnosis Result
          </h2>
        </div>
        {typeof diagnosis.confidence === "number" && (
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-950/60 px-3 py-1 text-xs font-semibold text-emerald-400 ring-1 ring-emerald-500/30">
            <Zap className="h-3.5 w-3.5" />
            Confidence: {diagnosis.confidence}%
          </div>
        )}
      </div>

      <div className="mt-5 space-y-5">
        {/* Root Cause */}
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Root Cause
          </span>
          <p className="mt-1 text-lg font-semibold text-rose-300 sm:text-xl">
            {diagnosis.root_cause || "No root cause identified"}
          </p>
        </div>

        {/* Explanation */}
        {diagnosis.explanation && (
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Explanation
            </span>
            <p className="mt-1 text-sm leading-relaxed text-slate-300 whitespace-pre-line">
              {diagnosis.explanation}
            </p>
          </div>
        )}

        {/* Suggested Fix */}
        {diagnosis.fix && (
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Suggested Fix
            </span>
            <p className="mt-1 text-sm leading-relaxed text-emerald-300/90 whitespace-pre-line">
              {diagnosis.fix}
            </p>
          </div>
        )}

        {/* Command */}
        {diagnosis.kubectl_commands && diagnosis.kubectl_commands.length > 0 && (
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              kubectl Command
            </span>
            <div className="mt-1.5 space-y-2">
              {diagnosis.kubectl_commands.map((cmd, idx) => (
                <div
                  key={idx}
                  className="group relative flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-4 py-2.5 font-mono text-xs text-sky-300"
                >
                  <div className="flex items-center gap-2 overflow-x-auto">
                    <Terminal className="h-4 w-4 shrink-0 text-slate-500" />
                    <span>{cmd}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleCopy(cmd, idx)}
                    className="ml-3 inline-flex items-center gap-1 rounded bg-slate-800 px-2 py-1 text-[11px] font-sans font-medium text-slate-300 transition hover:bg-slate-700 hover:text-white"
                  >
                    {copiedIndex === idx ? (
                      <>
                        <Check className="h-3 w-3 text-emerald-400" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3 text-slate-400" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
