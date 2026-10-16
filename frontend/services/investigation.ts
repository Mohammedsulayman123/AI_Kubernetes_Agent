import { apiClient } from "./api";
import { insforge } from "./insforge";
import type {
  InvestigationRecord,
  InvestigationResponse,
} from "@/types/investigation";

/**
 * Triggers backend Kubernetes investigation + AI reasoning.
 */
export async function runInvestigation(
  channel: string = "investigations",
  context: string | null = null,
  namespace: string | null = null,
  podName: string | null = null
): Promise<InvestigationResponse> {
  const response = await apiClient.post<InvestigationResponse>(
    "/investigate",
    { channel, context, namespace, pod_name: podName },
    { timeout: 120000 }
  );
  return response.data;
}

/**
 * Saves completed investigation to InsForge database.
 */
export async function saveInvestigation(
  record: Omit<InvestigationRecord, "id" | "created_at">
): Promise<InvestigationRecord | null> {
  try {
    const { data, error } = await insforge.database
      .from("investigations")
      .insert([record])
      .select();

    if (error) {
      console.error("Failed to save investigation to InsForge:", error);
      return null;
    }
    return (data && data[0]) ? (data[0] as InvestigationRecord) : null;
  } catch (err) {
    console.error("Error saving investigation:", err);
    return null;
  }
}

/**
 * Loads recent investigations from InsForge database.
 */
export async function fetchInvestigations(userId: string): Promise<InvestigationRecord[]> {
  try {
    const { data, error } = await insforge.database
      .from("investigations")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(10);

    if (error) {
      console.error("Failed to fetch investigation history:", error);
      return [];
    }
    return (data as InvestigationRecord[]) || [];
  } catch (err) {
    console.error("Error fetching investigation history:", err);
    return [];
  }
}
