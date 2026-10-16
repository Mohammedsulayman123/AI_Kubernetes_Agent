export interface ProblematicPod {
  name: string;
  namespace: string;
  status: string;
  message?: string | null;
  age_seconds?: number | null;
}

export interface PodInvestigation {
  healthy: boolean;
  problematic_pods: ProblematicPod[];
  total_pods: number;
  error?: string | null;
}

export interface PodLogSnippet {
  name: string;
  namespace: string;
  lines: string[];
  error?: string | null;
}

export interface LogsInvestigation {
  failed_pod_logs: PodLogSnippet[];
  error?: string | null;
}

export interface EventFinding {
  reason: string;
  namespace: string;
  object_kind: string;
  object_name: string;
  count: number;
  message: string;
}

export interface EventsInvestigation {
  healthy: boolean;
  findings: EventFinding[];
  error?: string | null;
}

export interface UnhealthyDeployment {
  name: string;
  namespace: string;
  desired_replicas: number;
  available_replicas: number;
  unavailable_replicas: number;
  conditions: string[];
  issue: string;
}

export interface DeploymentInvestigation {
  healthy: boolean;
  unhealthy_deployments: UnhealthyDeployment[];
  total_deployments: number;
  error?: string | null;
}

export interface NetworkIssue {
  service: string;
  namespace: string;
  issue: string;
  details: string;
}

export interface NetworkInvestigation {
  healthy: boolean;
  issues: NetworkIssue[];
  total_services: number;
  error?: string | null;
}

export interface InvestigationPayload {
  pods: PodInvestigation;
  logs: LogsInvestigation;
  events: EventsInvestigation;
  deployments: DeploymentInvestigation;
  network: NetworkInvestigation;
}

export interface Diagnosis {
  root_cause: string;
  explanation: string;
  fix: string;
  kubectl_commands: string[];
  prevention?: string;
  confidence: number;
  confidence_reasoning?: string;
  skipped?: boolean;
  error?: string | null;
}

export interface InvestigationResponse {
  status: string;
  investigation: InvestigationPayload;
  diagnosis?: Diagnosis | null;
  message?: string | null;
}

export interface InvestigationRecord {
  id?: string;
  user_id?: string | null;
  root_cause: string;
  explanation?: string;
  suggested_fix?: string;
  command?: string;
  namespace?: string;
  confidence: number;
  status: string;
  created_at?: string;
}

export type ProgressStepId =
  | "checking_pods"
  | "reading_logs"
  | "analyzing_events"
  | "inspecting_deployments"
  | "checking_networking"
  | "ai_reasoning"
  | "root_cause_found";

export interface ProgressStepItem {
  id: ProgressStepId;
  label: string;
  status: "pending" | "running" | "completed" | "error";
}
