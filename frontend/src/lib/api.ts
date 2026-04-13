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
    agentRuns: number;
    successRate: number;
  };
}

export interface SessionInfo {
  authenticated: boolean;
  username: string;
  role: "admin" | "founder" | "operator" | "viewer" | "anonymous" | string;
  organization: {
    id: string;
    name: string;
    slug: string;
  };
}

export interface AuditLogEntry {
  id: number;
  actor: string;
  action: string;
  entityType: string;
  entityId: string;
  metadata: Record<string, unknown>;
  createdAt: string;
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
  abortRequested: boolean;
  archivedAt: string | null;
  usage: {
    input: number;
    output: number;
    total: number;
    estimatedCostUsd: string;
  };
  qualityGates: QualityGate[];
  approvalDecisions: Array<{
    id: number;
    decision: "approved" | "rejected" | string;
    reviewer: string;
    notes: string;
    createdAt: string;
  }>;
  workstreams: Array<{
    id: number;
    owner: string;
    title: string;
    description: string;
    status: string;
    result: string;
    agentTemplateId: string | null;
    agentRuns: Array<{
      id: number;
      sessionId: string;
      status: string;
      logs: Array<Record<string, unknown>>;
      usage: {
        input: number;
        output: number;
        estimatedCostUsd: string;
      };
      resultText: string;
      error: string;
      createdAt: string;
      startedAt: string | null;
      finishedAt: string | null;
    }>;
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

const JSON_HEADERS = { "Content-Type": "application/json" };

function getCsrfToken(): string {
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") {
      return value;
    }
  }
  return "";
}

function headersWithCsrf(extraHeaders?: Record<string, string>): Record<string, string> {
  const csrfToken = getCsrfToken();
  const headers: Record<string, string> = { ...extraHeaders };
  if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
  }
  return headers;
}

export async function fetchSession(): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/opc/auth/me/`);
  if (!response.ok) {
    throw new Error("Unable to load session.");
  }
  return response.json();
}

export async function login(username: string, password: string): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/opc/auth/login/`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error("Unable to sign in.");
  }
  return response.json();
}

export async function logout(): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/opc/auth/logout/`, {
    method: "POST",
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to sign out.");
  }
  return response.json();
}

export async function bootstrapFounder(username: string, password: string, organizationName: string): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/opc/auth/bootstrap/`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ username, password, organizationName }),
  });
  if (!response.ok) {
    throw new Error("Unable to bootstrap founder.");
  }
  return response.json();
}

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
    headers: headersWithCsrf(JSON_HEADERS),
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

export async function fetchMissions(params: { status?: string; search?: string; includeArchived?: boolean } = {}): Promise<{ missions: Mission[] }> {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set("status", params.status);
  if (params.search) searchParams.set("search", params.search);
  if (params.includeArchived) searchParams.set("includeArchived", "true");
  const query = searchParams.toString();
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error("Unable to load missions.");
  }
  return response.json();
}

export async function fetchAuditLogs(params: { action?: string; limit?: number } = {}): Promise<{ logs: AuditLogEntry[] }> {
  const searchParams = new URLSearchParams();
  if (params.action) searchParams.set("action", params.action);
  if (params.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  const response = await fetch(`${API_BASE_URL}/api/opc/audit-logs/${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error("Unable to load audit logs.");
  }
  return response.json();
}

export function missionExportUrl(id: string): string {
  return `${API_BASE_URL}/api/opc/missions/${id}/export/`;
}

export function missionLogUrl(id: string): string {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/missions/${id}/logs/`;
  url.search = "";
  return url.toString();
}

export function metricsLogUrl(): string {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = "/ws/metrics/";
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
    headers: headersWithCsrf(JSON_HEADERS),
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
    headers: headersWithCsrf(JSON_HEADERS),
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
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to delete template.");
  }
  return response.json();
}

export async function approveMission(id: string, notes?: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/approve/`, {
    method: "POST",
    headers: headersWithCsrf(JSON_HEADERS),
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
    headers: headersWithCsrf(JSON_HEADERS),
    body: JSON.stringify({ notes }),
  });
  if (!response.ok) {
    throw new Error("Unable to reject mission.");
  }
  return response.json();
}

export async function retryMission(id: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/retry/`, {
    method: "POST",
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to retry mission.");
  }
  return response.json();
}

export async function abortMission(id: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/abort/`, {
    method: "POST",
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to abort mission.");
  }
  return response.json();
}

export async function archiveMission(id: string): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${id}/archive/`, {
    method: "POST",
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to archive mission.");
  }
  return response.json();
}

export async function retryWorkstream(missionId: string, workstreamId: number): Promise<Mission> {
  const response = await fetch(`${API_BASE_URL}/api/opc/missions/${missionId}/workstreams/${workstreamId}/retry/`, {
    method: "POST",
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to retry workstream.");
  }
  return response.json();
}

export interface Invitation {
  id: string;
  email: string;
  role: string;
  status: "pending" | "accepted" | "revoked" | string;
  expiresAt: string;
  createdAt: string;
  invitedBy: string;
}

export async function fetchInvitations(): Promise<{ invitations: Invitation[] }> {
  const response = await fetch(`${API_BASE_URL}/api/opc/invitations/`);
  if (!response.ok) {
    throw new Error("Unable to load invitations.");
  }
  return response.json();
}

export async function createInvitation(email: string, role: string, expiresInDays?: number): Promise<Invitation> {
  const response = await fetch(`${API_BASE_URL}/api/opc/invitations/create/`, {
    method: "POST",
    headers: headersWithCsrf(JSON_HEADERS),
    body: JSON.stringify({ email, role, expiresInDays }),
  });
  if (!response.ok) {
    throw new Error("Unable to create invitation.");
  }
  return response.json();
}

export async function revokeInvitation(invitationId: string): Promise<{ revoked: string }> {
  const response = await fetch(`${API_BASE_URL}/api/opc/invitations/${invitationId}/revoke/`, {
    method: "DELETE",
    headers: headersWithCsrf(),
  });
  if (!response.ok) {
    throw new Error("Unable to revoke invitation.");
  }
  return response.json();
}

export async function acceptInvitation(token: string, username: string, password: string): Promise<SessionInfo> {
  const response = await fetch(`${API_BASE_URL}/api/opc/invitations/${token}/accept/`, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error("Unable to accept invitation.");
  }
  return response.json();
}
