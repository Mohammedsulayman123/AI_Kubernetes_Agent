"use client";

import React, { useEffect, useState } from "react";
import {
  Server,
  ChevronDown,
  Loader2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
} from "lucide-react";
import { getClusters, type ClusterContext } from "@/services/clusters";

interface ClusterSelectorProps {
  selectedContext: string | null;
  onSelect: (context: string | null) => void;
}

export function ClusterSelector({
  selectedContext,
  onSelect,
}: ClusterSelectorProps) {
  const [clusters, setClusters] = useState<ClusterContext[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    const result = await getClusters();
    if (result.error) {
      setError(result.error);
      setClusters([]);
    } else {
      setClusters(result.clusters);
      // Auto-select current context if none already chosen
      if (!selectedContext && result.current_context) {
        onSelect(result.current_context);
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = clusters.find((c) => c.context === selectedContext);

  const handlePick = (ctx: ClusterContext) => {
    onSelect(ctx.context);
    setOpen(false);
  };

  // ── Loading ──────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm text-slate-400">
        <Loader2 className="h-4 w-4 animate-spin text-sky-400" />
        <span>Loading clusters…</span>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-950/20 p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-amber-300">No clusters found</p>
            <p className="mt-0.5 text-xs text-amber-400/80 whitespace-pre-line">
              {error}
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            className="shrink-0 inline-flex items-center gap-1 rounded bg-amber-900/40 px-2 py-1 text-xs font-medium text-amber-200 hover:bg-amber-900/60"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (clusters.length === 0) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-xs text-slate-500">
        No Kubernetes contexts found in kubeconfig.
      </div>
    );
  }

  // ── Selector ─────────────────────────────────────────────────────────────
  return (
    <div className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 transition hover:border-sky-500/50 hover:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-sky-500/30"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <Server className="h-4 w-4 shrink-0 text-sky-400" />
          <div className="min-w-0 text-left">
            <p className="font-medium truncate">
              {selected ? selected.context : "Select a cluster…"}
            </p>
            {selected && (
              <p className="text-xs text-slate-500 truncate mt-0.5">
                {selected.server || selected.cluster}
              </p>
            )}
          </div>
        </div>
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-slate-400 transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/40 overflow-hidden">
          <div className="max-h-60 overflow-y-auto divide-y divide-slate-800">
            {clusters.map((c) => (
              <button
                key={c.context}
                type="button"
                onClick={() => handlePick(c)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left transition text-sm ${
                  c.context === selectedContext
                    ? "bg-sky-500/10 text-sky-300"
                    : "text-slate-300 hover:bg-slate-800"
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{c.context}</span>
                    {c.is_current && (
                      <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                        default
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 truncate mt-0.5">
                    {c.server || c.cluster}
                  </p>
                </div>
                {c.context === selectedContext && (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-sky-400" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Backdrop to close */}
      {open && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setOpen(false)}
        />
      )}
    </div>
  );
}
