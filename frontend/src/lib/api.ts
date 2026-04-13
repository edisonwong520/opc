export interface ExecutiveAgent {
  id: string;
  name: string;
  title: string;
  mission: string;
  reportsTo: string | null;
  status: "ready" | "standby" | string;
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
  team: ExecutiveAgent[];
  pipeline: PipelineStep[];
  metrics: {
    agentsReady: number;
    activeMissions: number;
    budgetUsedUsd: number;
    qualityGates: number;
  };
}

export interface CommandPlan {
  id: string;
  command: string;
  status: string;
  nextStep: string;
  workstreams: Array<{ agent: string; task: string }>;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchBriefing(): Promise<DeskBriefing> {
  const response = await fetch(`${API_BASE_URL}/api/desk/briefing/`);
  if (!response.ok) {
    throw new Error("Unable to load CEO Desk briefing.");
  }
  return response.json();
}

export async function createCommand(command: string): Promise<CommandPlan> {
  const response = await fetch(`${API_BASE_URL}/api/desk/commands/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command }),
  });
  if (!response.ok) {
    throw new Error("Unable to create command plan.");
  }
  return response.json();
}
