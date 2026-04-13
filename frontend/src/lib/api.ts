export interface ExecutiveAgent {
  id: string;
  name: string;
  title: string;
  mission: string;
  reportsTo: string | null;
  status: "ready" | "standby" | string;
  tools: string[];
  modelPreference: string;
  budgetLimitUsd: string;
}

export interface PipelineStep {
  id: string;
  label: string;
  owner: string;
  state: "done" | "active" | "queued" | string;
}

export interface DeskBriefing {
  product: string;
  positioning: string;
  gateway: string;
  integration: string;
  authMode: string;
  openclaw: {
    health: {
      ok: boolean;
      rpcOk: boolean;
      pairingRequired: boolean;
      listening: boolean;
      gatewayUrl: string;
      authMode: string;
    };
    model: {
      ok: boolean;
      defaultModel: string;
      resolvedDefault: string;
      missingProvidersInUse: string[];
    };
  };
  team: ExecutiveAgent[];
  pipeline: PipelineStep[];
  metrics: {
    agentsReady: number;
    activeMissions: number;
    budgetUsedUsd: number;
    qualityGates: number;
  };
}

export interface MissionEvent {
  id: number;
  type: string;
  level: string;
  message: string;
  payload: Record<string, unknown>;
  createdAt: string;
}

export interface QualityGate {
  id: number;
  name: string;
  status: "pending" | "passed" | "failed" | string;
  details: string;
  updatedAt: string;
}

export interface Mission {
  id: string;
  command: string;
  sessionId: string;
  agentId: string;
  status: string;
  resultText: string;
  error: string;
  usage: {
    input: number;
    output: number;
    total: number;
    estimatedCostUsd: string;
  };
  qualityGates: QualityGate[];
  workstreams: Array<{
    id: number;
    owner: string;
    title: string;
    description: string;
    status: string;
    result: string;
    agentTemplateId: string | null;
    updatedAt: string;
  }>;
  boardBrief: {
    id: number;
    title: string;
    summary: string;
    recommendations: string[];
    risks: string[];
    sources: Array<Record<string, unknown>>;
    updatedAt: string;
  } | null;
  events?: MissionEvent[];
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchBriefing(): Promise<DeskBriefing> {
  const response = await fetch(`${API_BASE_URL}/api/opc/briefing/`);
  if (!response.ok) {
    throw new Error("Unable to load OPC briefing.");
  }
  return response.json();
}

export async function createCommand(command: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/commands/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command }),
  });
  if (!response.ok) {
    throw new Error("Unable to create command plan.");
  }
  return response.json();
}

export async function fetchMission(id: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/`);
  if (!response.ok) {
    throw new Error("Unable to load mission.");
  }
  return response.json();
}

export function missionLogUrl(id: string): string {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/missions/${id}/logs/`;
  url.search = "";
  return url.toString();
}

export async function fetchTemplates(): Promise<{ templates: ExecutiveAgent[] }> {
  const response = await fetch(`${API_BASE_URL}/api/opc/templates/`);
  if (!response.ok) {
    throw new Error("Unable to load templates.");
  }
  return response.json();
}

export interface TemplateInput {
  id: string;
  name: string;
  title?: string;
  mission?: string;
  reportsTo?: string;
  status?: string;
  tools?: string[];
  modelPreference?: string;
  budgetLimitUsd?: number;
  sortOrder?: number;
}

export async function createTemplate(data: TemplateInput): Promise<ExecutiveAgent> {
  const response = await fetch(`${API_BASE_URL}/api/opc/templates/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error("Unable to create template.");
  }
  return response.json();
}

export async function updateTemplate(id: string, data: Partial<TemplateInput>): Promise<ExecutiveAgent> {
  const response = await fetch(`${API_BASE_URL}/api/opc/templates/${id}/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    throw new Error("Unable to update template.");
  }
  return response.json();
}

export async function deleteTemplate(id: string): Promise<{ deleted: string }> {
  const response = await fetch(`${API_BASE_URL}/api/opc/templates/${id}/`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error("Unable to delete template.");
  }
  return response.json();
}

export async function approveMission(id: string, notes?: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/approve/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
  if (!response.ok) {
    throw new Error("Unable to approve mission.");
  }
  return response.json();
}

export async function rejectMission(id: string, notes?: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/reject/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes }),
  });
  if (!response.ok) {
    throw new Error("Unable to reject mission.");
  }
  return response.json();
}
