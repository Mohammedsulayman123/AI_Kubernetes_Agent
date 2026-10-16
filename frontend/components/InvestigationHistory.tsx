"use client";

import React from "react";
import { History, Clock, ArrowRight, Database } from "lucide-react";
import type { InvestigationRecord } from "@/types/investigation";

interface InvestigationHistoryProps {
  records: InvestigationRecord[];
  loading: boolean;
  onSelectRecord?: (record: InvestigationRecord) => void;
}

export function InvestigationHistory({
  records,
  loading,
  onSelectRecord,
}: InvestigationHistoryProps) {
  const formatDate = (isoStr?: string) => {
    if (!isoStr) return "Just now";
    try {
      const d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return isoStr;
    }
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6 shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-sky-400" />
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
            Previous Investigations
          </h2>
        </div>
        <span className="flex items-center gap-1 text-xs text-slate-500 font-mono">
          <Database className="h-3 w-3" />
          InsForge History
        </span>
      </div>

      <div className="mt-4">
        {loading ? (
          <div className="py-8 text-center text-xs text-slate-500">
            Loading history from InsForge...
          </div>
        ) : records.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500">
            No previous investigations recorded yet. Click &ldquo;Investigate Cluster&rdquo; above.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="py-2.5 font-medium">Root Cause</th>
                  <th className="py-2.5 font-medium">Namespace</th>
                  <th className="py-2.5 font-medium">Confidence</th>
                  <th className="py-2.5 font-medium">Status</th>
                  <th className="py-2.5 font-medium">Time</th>
                  {onSelectRecord && <th className="py-2.5 text-right font-medium">Action</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {records.map((item, index) => (
                  <tr
                    key={item.id || index}
                    onClick={() => onSelectRecord && onSelectRecord(item)}
                    className="group cursor-pointer transition-colors hover:bg-slate-800/40"
                  >
                    <td className="py-3 font-semibold text-slate-200 group-hover:text-sky-300">
                      {item.root_cause || "Cluster Investigation"}
                    </td>
                    <td className="py-3 font-mono text-slate-400">
                      {item.namespace || "default"}
                    </td>
                    <td className="py-3">
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-emerald-400">
                        {item.confidence || 0}%
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="inline-flex items-center gap-1 text-[11px] font-medium text-sky-400">
                        <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                        {item.status || "completed"}
                      </span>
                    </td>
                    <td className="py-3 text-slate-500">
                      <span className="inline-flex items-center gap-1 font-mono">
                        <Clock className="h-3 w-3" />
                        {formatDate(item.created_at)}
                      </span>
                    </td>
                    {onSelectRecord && (
                      <td className="py-3 text-right">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 text-slate-400 group-hover:text-sky-400"
                        >
                          <span>View</span>
                          <ArrowRight className="h-3 w-3" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
