<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  approveMission,
  createCommand,
  deleteTemplate,
  fetchBriefing,
  fetchMission,
  fetchTemplates,
  missionLogUrl,
  rejectMission,
  updateTemplate,
  type DeskBriefing,
  type ExecutiveAgent,
  type Mission,
  type MissionEvent,
  type TemplateInput,
} from "./lib/api";

const briefing = ref<DeskBriefing | null>(null);
const command = ref("Evaluate the OPC MVP delivery plan and return this week's action list.");
const mission = ref<Mission | null>(null);
const liveEvents = ref<MissionEvent[]>([]);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const socket = ref<WebSocket | null>(null);

const templates = ref<ExecutiveAgent[]>([]);
const showEditor = ref(false);
const editingTemplate = ref<ExecutiveAgent | null>(null);
const editForm = ref<TemplateInput>({ id: "", name: "" });
const savingTemplate = ref(false);

const topAgent = computed(() => briefing.value?.team.find((agent) => agent.id === "ceo"));
const directReports = computed(() => briefing.value?.team.filter((agent) => agent.reportsTo === "coo") ?? []);
const pendingApprovalGate = computed(() => mission.value?.qualityGates.find((gate) => gate.name === "founder-approval" && gate.status === "pending"));

async function loadBriefing() {
  try {
    loading.value = true;
    briefing.value = await fetchBriefing();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "OPC is temporarily unreachable.";
  } finally {
    loading.value = false;
  }
}

async function loadTemplates() {
  try {
    const result = await fetchTemplates();
    templates.value = result.templates;
  } catch (caught) {
    console.error("Failed to load templates:", caught);
  }
}

async function submitCommand() {
  if (!command.value.trim()) {
    return;
  }
  try {
    submitting.value = true;
    mission.value = await createCommand(command.value.trim());
    liveEvents.value = mission.value.events ?? [];
    connectMissionSocket(mission.value.id);
    void pollMission(mission.value.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Command dispatch failed.";
  } finally {
    submitting.value = false;
  }
}

function connectMissionSocket(id: string) {
  socket.value?.close();
  socket.value = new WebSocket(missionLogUrl(id));
  socket.value.onmessage = (event) => {
    const parsed = JSON.parse(event.data) as MissionEvent;
    liveEvents.value = [...liveEvents.value, parsed].slice(-80);
    if (parsed.type === "status" && parsed.payload && "status" in parsed.payload) {
      void fetchMission(id).then((fresh) => {
        mission.value = fresh;
        liveEvents.value = fresh.events ?? liveEvents.value;
      });
    }
  };
}

async function pollMission(id: string) {
  for (let i = 0; i < 180; i += 1) {
    const fresh = await fetchMission(id);
    mission.value = fresh;
    liveEvents.value = fresh.events ?? liveEvents.value;
    if (!["queued", "running"].includes(fresh.status)) {
      return;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 2000));
  }
}

function openEditor() {
  showEditor.value = true;
  void loadTemplates();
}

function startEdit(template: ExecutiveAgent) {
  editingTemplate.value = template;
  editForm.value = {
    id: template.id,
    name: template.name,
    title: template.title,
    mission: template.mission,
    reportsTo: template.reportsTo ?? "",
    status: template.status,
    tools: template.tools,
    modelPreference: template.modelPreference,
    budgetLimitUsd: parseFloat(template.budgetLimitUsd) || 0,
  };
}

function cancelEdit() {
  editingTemplate.value = null;
  editForm.value = { id: "", name: "" };
}

async function saveTemplate() {
  try {
    savingTemplate.value = true;
    if (editingTemplate.value) {
      await updateTemplate(editingTemplate.value.id, editForm.value);
    } else {
      await updateTemplate(editForm.value.id, editForm.value);
    }
    await loadTemplates();
    await loadBriefing();
    cancelEdit();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Failed to save template.";
  } finally {
    savingTemplate.value = false;
  }
}

async function removeTemplate(id: string) {
  try {
    await deleteTemplate(id);
    await loadTemplates();
    await loadBriefing();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Failed to delete template.";
  }
}

async function handleApprove() {
  if (!mission.value) return;
  try {
    mission.value = await approveMission(mission.value.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Approval failed.";
  }
}

async function handleReject() {
  if (!mission.value) return;
  try {
    mission.value = await rejectMission(mission.value.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Rejection failed.";
  }
}

onMounted(loadBriefing);
</script>

<template>
  <main class="min-h-screen bg-[#eef2ef] text-[#171717]">
    <section class="workspace-grid min-h-screen px-5 py-5 sm:px-8 lg:px-10">
      <aside class="command-rail">
        <p class="eyebrow">OpenClaw Executive OS</p>
        <h1>OPC</h1>
        <p class="lede">Give one founder command to an AI leadership team. COO decomposes, CTO/CFO/CMO work in parallel, and CEO returns the board brief.</p>

        <form class="command-box" @submit.prevent="submitCommand">
          <label for="command">Founder Command</label>
          <textarea id="command" v-model="command" rows="7" />
          <button type="submit" :disabled="submitting">
            {{ submitting ? "Dispatching..." : "Assign to Executive Team" }}
          </button>
        </form>

        <div v-if="mission" class="dispatch">
          <p class="dispatch-title">{{ mission.status }}</p>
          <p>Session {{ mission.sessionId }}</p>
          <ul>
            <li v-for="gate in mission.qualityGates" :key="gate.id">
              <strong>{{ gate.name }}</strong>
              <span>{{ gate.status }}</span>
            </li>
          </ul>
          <div v-if="pendingApprovalGate" class="approval-actions">
            <button class="approve-btn" @click="handleApprove" :disabled="savingTemplate">Approve</button>
            <button class="reject-btn" @click="handleReject" :disabled="savingTemplate">Reject</button>
          </div>
        </div>
      </aside>

      <section class="board">
        <div v-if="loading" class="notice">Connecting to OPC API...</div>
        <div v-else-if="error" class="notice error">{{ error }}</div>

        <template v-else-if="briefing">
          <header class="board-header">
            <div>
              <p class="eyebrow">Mission Control</p>
              <h2>{{ briefing.positioning }}</h2>
            </div>
            <div class="runtime">
              <span>{{ briefing.integration }}</span>
              <small>{{ briefing.gateway }} · {{ briefing.authMode }}</small>
            </div>
          </header>

          <section class="openclaw-strip">
            <article :class="{ good: briefing.openclaw.health.ok, warn: !briefing.openclaw.health.rpcOk }">
              <span>Gateway</span>
              <strong>{{ briefing.openclaw.health.ok ? "running" : "degraded" }}</strong>
              <p>{{ briefing.openclaw.health.rpcOk ? "RPC probe ok" : "CLI available, RPC pairing may be required" }}</p>
            </article>
            <article :class="{ good: briefing.openclaw.model.ok }">
              <span>Model</span>
              <strong>{{ briefing.openclaw.model.resolvedDefault || "not configured" }}</strong>
              <p>{{ briefing.openclaw.model.missingProvidersInUse.length ? "provider missing" : "provider ready" }}</p>
            </article>
          </section>

          <section class="metrics" aria-label="OPC metrics">
            <article>
              <span>{{ briefing.metrics.agentsReady }}</span>
              <p>Agents Ready</p>
            </article>
            <article>
              <span>{{ briefing.metrics.activeMissions }}</span>
              <p>Active Mission</p>
            </article>
            <article>
              <span>${{ briefing.metrics.budgetUsedUsd.toFixed(2) }}</span>
              <p>Budget Used</p>
            </article>
            <article>
              <span>{{ briefing.metrics.qualityGates }}</span>
              <p>Quality Gates</p>
            </article>
          </section>

          <section class="org-map">
            <button class="edit-team-btn" @click="openEditor">Edit Team</button>
            <article v-if="topAgent" class="agent-card ceo-card">
              <span>{{ topAgent.name }}</span>
              <h3>{{ topAgent.title }}</h3>
              <p>{{ topAgent.mission }}</p>
            </article>

            <div class="agent-row">
              <article v-for="agent in briefing.team.filter((item) => item.reportsTo === 'ceo')" :key="agent.id" class="agent-card coo-card">
                <span>{{ agent.name }}</span>
                <h3>{{ agent.title }}</h3>
                <p>{{ agent.mission }}</p>
              </article>
            </div>

            <div class="agent-row reports">
              <article v-for="agent in directReports" :key="agent.id" class="agent-card">
                <span>{{ agent.name }}</span>
                <h3>{{ agent.title }}</h3>
                <p>{{ agent.mission }}</p>
                <small>{{ agent.status }} · {{ agent.tools.length }} tools</small>
              </article>
            </div>
          </section>

          <section class="pipeline">
            <h2>Execution Pipeline</h2>
            <div class="pipeline-track">
              <article v-for="step in briefing.pipeline" :key="step.id" :class="['step', step.state]">
                <span>{{ step.state }}</span>
                <h3>{{ step.label }}</h3>
                <p>{{ step.owner }}</p>
              </article>
            </div>
          </section>

          <section v-if="mission" class="mission-console">
            <div>
              <p class="eyebrow">OpenClaw Mission</p>
              <h2>{{ mission.status }}</h2>
              <p v-if="mission.boardBrief" class="result-text">{{ mission.boardBrief.summary }}</p>
              <p v-else-if="mission.resultText" class="result-text">{{ mission.resultText }}</p>
              <p v-else-if="mission.error" class="result-text error-text">{{ mission.error }}</p>
              <p v-else class="result-text">OpenClaw is processing this Founder Command.</p>
            </div>
            <div class="usage-grid">
              <span>{{ mission.usage.input }}</span>
              <span>{{ mission.usage.output }}</span>
              <span>{{ mission.usage.total }}</span>
              <small>input / output / total tokens · ${{ mission.usage.estimatedCostUsd }}</small>
            </div>
            <div class="workstream-grid">
              <article v-for="workstream in mission.workstreams" :key="workstream.id">
                <span>{{ workstream.owner }} · {{ workstream.status }}</span>
                <strong>{{ workstream.title }}</strong>
                <p>{{ workstream.description }}</p>
              </article>
            </div>
            <div v-if="mission.boardBrief" class="brief-panel">
              <h3>{{ mission.boardBrief.title }}</h3>
              <ul>
                <li v-for="item in mission.boardBrief.recommendations" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="log-stream">
              <article v-for="event in liveEvents" :key="event.id">
                <span>{{ event.level }}</span>
                <p>{{ event.message }}</p>
              </article>
            </div>
          </section>
        </template>
      </section>
    </section>

    <div v-if="showEditor" class="modal-overlay" @click.self="showEditor = false">
      <div class="modal">
        <header class="modal-header">
          <h2>Agent Templates</h2>
          <button class="close-btn" @click="showEditor = false">×</button>
        </header>
        <div class="modal-body">
          <div v-if="editingTemplate" class="edit-form">
            <label>ID</label>
            <input v-model="editForm.id" disabled />
            <label>Name</label>
            <input v-model="editForm.name" />
            <label>Title</label>
            <input v-model="editForm.title" />
            <label>Mission</label>
            <textarea v-model="editForm.mission" rows="3" />
            <label>Status</label>
            <select v-model="editForm.status">
              <option value="ready">Ready</option>
              <option value="standby">Standby</option>
              <option value="disabled">Disabled</option>
            </select>
            <label>Budget Limit (USD)</label>
            <input v-model.number="editForm.budgetLimitUsd" type="number" step="0.01" />
            <div class="form-actions">
              <button class="save-btn" @click="saveTemplate" :disabled="savingTemplate">{{ savingTemplate ? "Saving..." : "Save" }}</button>
              <button class="cancel-btn" @click="cancelEdit">Cancel</button>
            </div>
          </div>
          <div v-else class="template-list">
            <article v-for="t in templates" :key="t.id" class="template-item">
              <div>
                <strong>{{ t.name }}</strong>
                <span>{{ t.title }}</span>
                <small>{{ t.status }}</small>
              </div>
              <div class="template-actions">
                <button @click="startEdit(t)">Edit</button>
                <button class="delete-btn" @click="removeTemplate(t.id)">Delete</button>
              </div>
            </article>
          </div>
        </div>
      </div>
    </div>
  </main>
</template>
