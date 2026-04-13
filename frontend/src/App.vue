<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  abortMission,
  approveMission,
  archiveMission,
  createCommand,
  fetchBriefing,
  fetchMission,
  fetchMissions,
  fetchSession,
  missionExportUrl,
  metricsLogUrl,
  missionLogUrl,
  rejectMission,
  retryMission,
  retryWorkstream,
  type DeskBriefing,
  type Mission,
  type MissionEvent,
  type SessionInfo,
} from "./lib/api";
import AuditLogPanel from "./components/AuditLogPanel.vue";
import AuthPanel from "./components/AuthPanel.vue";
import InvitationPanel from "./components/InvitationPanel.vue";
import OrgChart from "./components/OrgChart.vue";
import TemplateEditor from "./components/TemplateEditor.vue";

const briefing = ref<DeskBriefing | null>(null);
const session = ref<SessionInfo | null>(null);
const command = ref("Evaluate the OPC MVP delivery plan and return this week's action list.");
const mission = ref<Mission | null>(null);
const liveEvents = ref<MissionEvent[]>([]);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const socket = ref<WebSocket | null>(null);
const metricsSocket = ref<WebSocket | null>(null);

const showEditor = ref(false);
const approvalNotes = ref("");
const actingOnApproval = ref(false);
const actingOnMission = ref(false);
const retryingWorkstreamId = ref<number | null>(null);
const missionHistory = ref<Mission[]>([]);
const historySearch = ref("");
const historyStatus = ref("");
const loadingHistory = ref(false);

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

async function loadSession() {
  try {
    session.value = await fetchSession();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Session unavailable.";
  }
}

async function submitCommand() {
  if (!command.value.trim()) {
    return;
  }
  try {
    submitting.value = true;
    mission.value = await createCommand(command.value.trim());
    void loadMissionHistory();
    liveEvents.value = mission.value.events ?? [];
    connectMissionSocket(mission.value.id);
    void pollMission(mission.value.id);
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Command dispatch failed.";
  } finally {
    submitting.value = false;
  }
}

async function loadMissionHistory() {
  try {
    loadingHistory.value = true;
    const result = await fetchMissions({ status: historyStatus.value, search: historySearch.value });
    missionHistory.value = result.missions;
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Mission history unavailable.";
  } finally {
    loadingHistory.value = false;
  }
}

async function openMission(id: string) {
  mission.value = await fetchMission(id);
  liveEvents.value = mission.value.events ?? [];
  if (["queued", "running"].includes(mission.value.status)) {
    connectMissionSocket(mission.value.id);
    void pollMission(mission.value.id);
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

function connectMetricsSocket() {
  metricsSocket.value?.close();
  metricsSocket.value = new WebSocket(metricsLogUrl());
  metricsSocket.value.onmessage = (event) => {
    const parsed = JSON.parse(event.data) as { type: string; metrics: DeskBriefing["metrics"] };
    if (parsed.type === "metrics" && briefing.value) {
      briefing.value = { ...briefing.value, metrics: parsed.metrics };
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
}

function handleSessionChanged(nextSession: SessionInfo) {
  session.value = nextSession;
  void loadBriefing();
  void loadMissionHistory();
}

async function handleApprove() {
  if (!mission.value) return;
  try {
    actingOnApproval.value = true;
    mission.value = await approveMission(mission.value.id, approvalNotes.value);
    approvalNotes.value = "";
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Approval failed.";
  } finally {
    actingOnApproval.value = false;
  }
}

async function handleReject() {
  if (!mission.value) return;
  try {
    actingOnApproval.value = true;
    mission.value = await rejectMission(mission.value.id, approvalNotes.value);
    approvalNotes.value = "";
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Rejection failed.";
  } finally {
    actingOnApproval.value = false;
  }
}

async function handleAbort() {
  if (!mission.value) return;
  try {
    actingOnMission.value = true;
    mission.value = await abortMission(mission.value.id);
    void loadMissionHistory();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Abort failed.";
  } finally {
    actingOnMission.value = false;
  }
}

async function handleRetry() {
  if (!mission.value) return;
  try {
    actingOnMission.value = true;
    mission.value = await retryMission(mission.value.id);
    liveEvents.value = mission.value.events ?? [];
    connectMissionSocket(mission.value.id);
    void pollMission(mission.value.id);
    void loadMissionHistory();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Retry failed.";
  } finally {
    actingOnMission.value = false;
  }
}

async function handleArchive() {
  if (!mission.value) return;
  try {
    actingOnMission.value = true;
    mission.value = await archiveMission(mission.value.id);
    void loadMissionHistory();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Archive failed.";
  } finally {
    actingOnMission.value = false;
  }
}

async function handleWorkstreamRetry(workstreamId: number) {
  if (!mission.value) return;
  try {
    retryingWorkstreamId.value = workstreamId;
    mission.value = await retryWorkstream(mission.value.id, workstreamId);
    liveEvents.value = mission.value.events ?? [];
    void loadMissionHistory();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "Workstream retry failed.";
  } finally {
    retryingWorkstreamId.value = null;
  }
}

onMounted(() => {
  void loadSession();
  void loadBriefing();
  void loadMissionHistory();
  connectMetricsSocket();
});
</script>

<template>
  <main class="min-h-screen bg-[#eef2ef] text-[#171717]">
    <section class="workspace-grid min-h-screen px-5 py-5 sm:px-8 lg:px-10">
      <aside class="command-rail">
        <p class="eyebrow">OpenClaw Executive OS</p>
        <h1>OPC</h1>
        <p class="lede">Give one founder command to an AI leadership team. COO decomposes, CTO/CFO/CMO work in parallel, and CEO returns the board brief.</p>

        <AuthPanel
          :session="session"
          @changed="handleSessionChanged"
          @error="(message) => (error = message)"
        />

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
            <label for="approval-notes">Review Notes</label>
            <textarea id="approval-notes" v-model="approvalNotes" rows="3" placeholder="Decision notes for this mission" />
            <div>
              <button class="approve-btn" @click="handleApprove" :disabled="actingOnApproval">Approve</button>
              <button class="reject-btn" @click="handleReject" :disabled="actingOnApproval">Reject</button>
            </div>
          </div>
          <div class="mission-actions">
            <button v-if="['queued', 'running'].includes(mission.status)" @click="handleAbort" :disabled="actingOnMission">Abort</button>
            <button v-if="['failed', 'aborted'].includes(mission.status)" @click="handleRetry" :disabled="actingOnMission">Retry</button>
            <button v-if="!['queued', 'running'].includes(mission.status) && !mission.archivedAt" @click="handleArchive" :disabled="actingOnMission">Archive</button>
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
            <article>
              <span>{{ briefing.metrics.agentRuns }}</span>
              <p>Agent Runs</p>
            </article>
            <article>
              <span>{{ Math.round(briefing.metrics.successRate * 100) }}%</span>
              <p>Success Rate</p>
            </article>
          </section>

          <OrgChart :agents="briefing.team" @edit="openEditor" />

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

          <section class="mission-history">
            <div class="history-header">
              <h2>Mission History</h2>
              <div class="history-filters">
                <input v-model="historySearch" placeholder="Search commands" @keyup.enter="loadMissionHistory" />
                <select v-model="historyStatus" @change="loadMissionHistory">
                  <option value="">All Statuses</option>
                  <option value="queued">Queued</option>
                  <option value="running">Running</option>
                  <option value="succeeded">Succeeded</option>
                  <option value="failed">Failed</option>
                  <option value="aborted">Aborted</option>
                </select>
                <button @click="loadMissionHistory" :disabled="loadingHistory">{{ loadingHistory ? "Loading..." : "Filter" }}</button>
              </div>
            </div>
            <div class="history-list">
              <article v-for="item in missionHistory" :key="item.id" :class="{ active: mission?.id === item.id }">
                <button @click="openMission(item.id)">
                  <strong>{{ item.status }}</strong>
                  <span>{{ item.command }}</span>
                  <small>{{ item.sessionId }} · ${{ item.usage.estimatedCostUsd }}</small>
                </button>
                <a :href="missionExportUrl(item.id)">Export</a>
              </article>
            </div>
          </section>

          <AuditLogPanel @error="(message) => (error = message)" />

          <InvitationPanel :session="session" @error="(message) => (error = message)" />

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
                <small v-if="workstream.agentRuns.length">
                  {{ workstream.agentRuns.at(-1)?.sessionId }} · ${{ workstream.agentRuns.at(-1)?.usage.estimatedCostUsd }}
                </small>
                <button
                  v-if="workstream.status === 'failed' && !['queued', 'running'].includes(mission.status)"
                  class="workstream-retry-btn"
                  @click="handleWorkstreamRetry(workstream.id)"
                  :disabled="retryingWorkstreamId === workstream.id"
                >
                  {{ retryingWorkstreamId === workstream.id ? "Retrying..." : "Retry Workstream" }}
                </button>
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

    <TemplateEditor
      v-if="showEditor"
      @close="showEditor = false"
      @saved="loadBriefing"
      @error="(message) => (error = message)"
    />
  </main>
</template>
