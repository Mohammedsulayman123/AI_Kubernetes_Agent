"use client";

import React from "react";
import { useAuth } from "./AuthContext";
import { AuthView } from "./AuthView";
import { Dashboard } from "./Dashboard";
import { Loader2 } from "lucide-react";

export function HomePage() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-400">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-sky-400" />
          <p className="text-sm font-medium">Verifying InsForge session...</p>
        </div>
      </main>
    );
  }

  if (!user) {
    return <AuthView />;
  }

  return <Dashboard />;
}
