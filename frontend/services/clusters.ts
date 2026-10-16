import { apiClient } from "./api";

export interface ClusterContext {
  context: string;
  cluster: string;
  namespace: string;
  server: string;
  is_current: boolean;
}

export interface ClustersResponse {
  current_context: string | null;
  clusters: ClusterContext[];
  error: string | null;
}

export interface PodOption {
  name: string;
  status: string;
}

export async function getNamespaces(context: string | null): Promise<string[]> {
  try {
    const response = await apiClient.get<{ namespaces: string[] }>("/namespaces", {
      params: context ? { context } : undefined,
    });
    return response.data.namespaces;
  } catch {
    return [];
  }
}

export async function getPods(
  namespace: string | null,
  context: string | null
): Promise<PodOption[]> {
  if (!namespace) return [];
  try {
    const response = await apiClient.get<{ pods: PodOption[] }>(
      `/namespaces/${encodeURIComponent(namespace)}/pods`,
      { params: context ? { context } : undefined }
    );
    return response.data.pods;
  } catch {
    return [];
  }
}

export async function getClusters(): Promise<ClustersResponse> {
  try {
    const response = await apiClient.get<ClustersResponse>("/clusters");
    return response.data;
  } catch (err: any) {
    const msg =
      err?.response?.data?.detail ||
      err?.message ||
      "Failed to load clusters from backend.";
    return { current_context: null, clusters: [], error: msg };
  }
}

export interface ScenarioInfo {
  id: string;
  title: string;
  description: string;
  namespace: string;
}

export interface ScenariosResponse {
  scenarios: ScenarioInfo[];
}

export async function getScenarios(): Promise<ScenarioInfo[]> {
  try {
    const response = await apiClient.get<ScenariosResponse>("/test-scenarios");
    return response.data.scenarios;
  } catch {
    return [];
  }
}

export async function applyScenario(
  scenarioId: string,
  context: string | null
): Promise<{ success: boolean; error?: string; title?: string; output?: string; namespace?: string }> {
  try {
    const response = await apiClient.post("/test-scenarios/apply", {
      scenario_id: scenarioId,
      context,
    });
    return response.data;
  } catch (err: any) {
    return {
      success: false,
      error: err?.response?.data?.detail || err?.message || "Failed to apply scenario.",
    };
  }
}

export async function cleanupScenario(
  scenarioId: string,
  context: string | null
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await apiClient.post("/test-scenarios/cleanup", {
      scenario_id: scenarioId,
      context,
    });
    return response.data;
  } catch (err: any) {
    return {
      success: false,
      error: err?.response?.data?.detail || err?.message || "Failed to cleanup scenario.",
    };
  }
}
