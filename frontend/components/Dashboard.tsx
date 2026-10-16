"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "./AuthContext";
import { InvestigationProgress } from "./InvestigationProgress";
import { RootCauseCard } from "./RootCauseCard";
import { InvestigationHistory } from "./InvestigationHistory";
import { ClusterSelector } from "./ClusterSelector";
import { getNamespaces, getPods, type PodOption } from "@/services/clusters";
import { TestScenarios } from "./TestScenarios";
import {
  runInvestigation,
  fetchInvestigations,
  saveInvestigation,
} from "@/services/investigation";
import { insforge } from "@/services/insforge";
import type {
  Diagnosis,
  InvestigationRecord,
  ProgressStepItem,
  ProgressStepId,
} from "@/types/investigation";
import {
  Play,
  Loader2,
  LogOut,
  Server,
  Activity,
  AlertCircle,
  RefreshCw,
  Cpu,
  CheckCircle2,
  Heart,
} from "lucide-react";

const INITIAL_STEPS: ProgressStepItem[] = [
  { id: "checking_pods", label: "Checking Pods", status: "pending" },
  { id: "reading_logs", label: "Reading Logs", status: "pending" },
  { id: "analyzing_events", label: "Analyzing Events", status: "pending" },
  { id: "inspecting_deployments", label: "Inspecting Deployments", status: "pending" },
  { id: "checking_networking", label: "Checking Networking", status: "pending" },
  { id: "ai_reasoning", label: "AI Reasoning", status: "pending" },
  { id: "root_cause_found", label: "Root Cause Found", status: "pending" },
];

export function Dashboard() {
  const { user, signOut } = useAuth();

  // ── Cluster selection ───────────────────────────────────────────────────
  const [selectedContext, setSelectedContext] = useState<string | null>(null);
  const [namespaceScope, setNamespaceScope] = useState("");
  const [podNameScope, setPodNameScope] = useState("");
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [pods, setPods] = useState<PodOption[]>([]);

  // ── Investigation state ─────────────────────────────────────────────────
  const [steps, setSteps] = useState<ProgressStepItem[]>(INITIAL_STEPS);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [clusterHealthy, setClusterHealthy] = useState<boolean | null>(null);
  const [records, setRecords] = useState<InvestigationRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isInvestigatingRef = useRef(false);

  // Load history
  const loadHistory = useCallback(async () => {
    if (!user?.id) {
      setRecords([]);
      setHistoryLoading(false);
      return;
    }
    setHistoryLoading(true);
    const data = await fetchInvestigations(user.id);
    setRecords(data);
    setHistoryLoading(false);
  }, [user?.id]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    setNamespaceScope("");
    setPodNameScope("");
    setPods([]);
    getNamespaces(selectedContext).then(setNamespaces);
  }, [selectedContext]);

  useEffect(() => {
    setPodNameScope("");
    getPods(namespaceScope || null, selectedContext).then(setPods);
  }, [namespaceScope, selectedContext]);

  // Connect InsForge Realtime
  useEffect(() => {
    let active = true;

    async function initRealtime() {
      try {
        await insforge.realtime.connect();
        await insforge.realtime.subscribe("investigations");

        insforge.realtime.on("progress", (event: any) => {
          if (!active || !event?.step) return;

          const stepId = event.step as ProgressStepId;
          const status = event.status as string; // "running" | "done" | "error"

          setSteps((prev) => {
            const stepOrder = INITIAL_STEPS.map((s) => s.id);
            const targetIdx = stepOrder.indexOf(stepId);
            if (targetIdx === -1) return prev;

            return prev.map((item, idx) => {
              if (status === "running" && idx === targetIdx) {
                return { ...item, status: "running" };
              }
              if (status === "done") {
                if (idx < targetIdx) return { ...item, status: "completed" };
                if (idx === targetIdx) return { ...item, status: "completed" };
                if (idx === targetIdx + 1) {
                  // Only mark the next step running if we haven't already done so
                  return item.status === "pending" ? { ...item, status: "running" } : item;
                }
              }
              return item;
            });
          });
        });
      } catch (err) {
        console.warn("Could not connect to InsForge Realtime:", err);
      }
    }

    initRealtime();

    return () => {
      active = false;
    };
  }, []);

  // ── Investigate handler ─────────────────────────────────────────────────
  const handleInvestigate = useCallback(async (
    namespace: string | null = namespaceScope.trim() || null,
    podName: string | null = podNameScope.trim() || null
  ) => {
    if (isInvestigatingRef.current) return;
    isInvestigatingRef.current = true;

    setErrorMsg(null);
    setDiagnosis(null);
    setClusterHealthy(null);
    setIsInvestigating(true);

    // Reset steps — first step is "running"
    setSteps(
      INITIAL_STEPS.map((step, idx) => ({
        ...step,
        status: idx === 0 ? "running" : "pending",
      }))
    );

    try {
      const response = await runInvestigation("investigations", selectedContext, namespace, podName);

      // Mark all steps complete
      setSteps((prev) =>
        prev.map((step) => ({ ...step, status: "completed" }))
      );

      if (response.message === "healthy") {
        // Cluster is healthy — no issues
        setClusterHealthy(true);
        setDiagnosis(null);
      } else if (response.diagnosis) {
        setClusterHealthy(false);
        setDiagnosis(response.diagnosis);

        const problematicPods = response.investigation?.pods?.problematic_pods || [];
        const ns =
          problematicPods.length > 0 ? problematicPods[0].namespace : "default";

        await saveInvestigation({
          user_id: user?.id || null,
          root_cause: response.diagnosis.root_cause || "Unknown",
          explanation: response.diagnosis.explanation || "",
          suggested_fix: response.diagnosis.fix || "",
          command: response.diagnosis.kubectl_commands?.[0] || "",
          namespace: ns,
          confidence: response.diagnosis.confidence || 0,
          status: response.status === "error" ? "failed" : "completed",
        });

        await loadHistory();
      } else if (response.status === "error") {
        setErrorMsg(
          response.message ||
            "Kubernetes cluster investigation failed. Check the backend logs."
        );
        setSteps((prev) =>
          prev.map((step) =>
            step.status === "running" ? { ...step, status: "error" } : step
          )
        );
      }
    } catch (err: any) {
      console.error("Investigation failed:", err);
      const msg =
        err?.response?.data?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "Investigation timed out or the backend is unreachable. Ensure FastAPI is running on port 8000.";
      setErrorMsg(msg);
      setSteps((prev) =>
        prev.map((step) =>
          step.status === "running" ? { ...step, status: "error" } : step
        )
      );
    } finally {
      setIsInvestigating(false);
      isInvestigatingRef.current = false;
    }
  }, [selectedContext, namespaceScope, podNameScope, user, loadHistory]);

  const handleSelectHistoryItem = (rec: InvestigationRecord) => {
    setClusterHealthy(null);
    setDiagnosis({
      root_cause: rec.root_cause,
      explanation: rec.explanation || "Historical investigation record.",
      fix: rec.suggested_fix || "",
      kubectl_commands: rec.command ? [rec.command] : [],
      confidence: rec.confidence || 0,
    });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* ── Top Header ───────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sky-500/10 text-sky-400 ring-1 ring-sky-500/20">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-slate-100">
                AI Kubernetes Agent
              </h1>
              <p className="text-xs text-slate-400">Senior SRE Troubleshooting Engine</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 rounded-full border border-slate-800 bg-slate-950/60 px-3 py-1 text-xs text-slate-300">
              <Activity className="h-3.5 w-3.5 text-emerald-400" />
              <span>Backend:</span>
              <span className="font-medium text-emerald-400">Connected</span>
            </div>

            <div className="flex items-center gap-3 border-l border-slate-800 pl-4">
              <span className="hidden md:inline text-xs font-mono text-slate-400">
                {user?.email || "Operator"}
              </span>
              <button
                type="button"
                onClick={() => signOut()}
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Content ────────────────────────────────────────────────── */}
      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">

        {/* ── Cluster Selector section ──────────────────────────────────── */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
          <div className="mb-4 flex items-center gap-2">
            <Server className="h-4 w-4 text-sky-400" />
            <h2 className="text-sm font-semibold text-slate-200">
              Select Kubernetes Cluster
            </h2>
            <span className="text-xs text-slate-500">— from your local kubeconfig</span>
          </div>
          <ClusterSelector
            selectedContext={selectedContext}
            onSelect={setSelectedContext}
          />
        </section>

        {/* ── Hero CTA Section ──────────────────────────────────────────── */}
        <section className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-900/40 p-8 shadow-xl">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full bg-sky-500/10 px-3 py-1 text-xs font-medium text-sky-400 ring-1 ring-sky-500/20 mb-3">
                <Server className="h-3.5 w-3.5" />
                Realtime Kubernetes Diagnostics
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-slate-50 sm:text-3xl">
                Troubleshoot Kubernetes Cluster
              </h2>
              <p className="mt-2 max-w-2xl text-sm text-slate-400">
                Inspect pods, logs, events, deployments, and networking simultaneously
                with AI root-cause analysis and actionable kubectl fixes.
                {selectedContext && (
                  <span className="ml-1 text-sky-400 font-medium">
                    Target: <code className="text-sky-300">{selectedContext}</code>
                  </span>
                )}
              </p>
            </div>

            <div className="flex flex-col gap-3 items-start md:items-end shrink-0">
              <label className="w-full md:w-64">
                <span className="mb-1 block text-xs font-medium text-slate-400">
                  Namespace scope (optional)
                </span>
                <select
                  value={namespaceScope}
                  onChange={(event) => setNamespaceScope(event.target.value)}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                >
                  <option value="">All namespaces</option>
                  {namespaces.map((namespace) => (
                    <option key={namespace} value={namespace}>{namespace}</option>
                  ))}
                </select>
              </label>
              <label className="w-full md:w-64">
                <span className="mb-1 block text-xs font-medium text-slate-400">
                  Pod name (optional)
                </span>
                <select
                  value={podNameScope}
                  onChange={(event) => setPodNameScope(event.target.value)}
                  disabled={!namespaceScope}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-500/20"
                >
                  <option value="">All pods</option>
                  {pods.map((pod) => (
                    <option key={pod.name} value={pod.name}>{pod.name} ({pod.status})</option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={() => handleInvestigate()}
                disabled={isInvestigating}
                className="inline-flex items-center justify-center gap-2.5 rounded-xl bg-sky-500 px-8 py-4 text-base font-semibold text-slate-950 shadow-lg shadow-sky-500/20 transition hover:bg-sky-400 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isInvestigating ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Investigating Cluster…</span>
                  </>
                ) : (
                  <>
                    <Play className="h-5 w-5 fill-current" />
                    <span>Investigate Cluster</span>
                  </>
                )}
              </button>

              {/* Test Scenarios button */}
              <TestScenarios
                selectedContext={selectedContext}
                onScenarioApplied={handleInvestigate}
              />
            </div>
          </div>

          {/* Error banner */}
          {errorMsg && (
            <div className="mt-6 flex items-start gap-3 rounded-xl border border-rose-500/30 bg-rose-950/30 p-4 text-sm text-rose-300">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
              <div className="flex-1">
                <p className="font-semibold text-rose-200">Investigation Error</p>
                <p className="mt-0.5 text-xs text-rose-300/90 whitespace-pre-line">
                  {errorMsg}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleInvestigate()}
                className="inline-flex items-center gap-1 rounded bg-rose-900/40 px-2.5 py-1 text-xs font-medium text-rose-200 hover:bg-rose-900/60"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
            </div>
          )}

          {/* Healthy cluster banner */}
          {clusterHealthy && !isInvestigating && (
            <div className="mt-6 flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 text-sm text-emerald-300">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" />
              <div>
                <p className="font-semibold text-emerald-200">
                  No critical Kubernetes issues detected.
                </p>
                <p className="mt-0.5 text-xs text-emerald-400/80">
                  Cluster appears healthy. All pods, deployments, events, and
                  networking look good.
                </p>
              </div>
              <Heart className="ml-auto h-5 w-5 text-emerald-500/60" />
            </div>
          )}
        </section>

        {/* ── Progress + Diagnosis Grid ─────────────────────────────────── */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <InvestigationProgress
              steps={steps}
              isInvestigating={isInvestigating}
            />
          </div>
          <div className="lg:col-span-7">
            <RootCauseCard
              diagnosis={diagnosis}
              clusterHealthy={clusterHealthy}
              isInvestigating={isInvestigating}
            />
          </div>
        </div>

        {/* ── Investigation History ─────────────────────────────────────── */}
        <div>
          <InvestigationHistory
            records={records}
            loading={historyLoading}
            onSelectRecord={handleSelectHistoryItem}
          />
        </div>
      </main>
    </div>
  );
}
