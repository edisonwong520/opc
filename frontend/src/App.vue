<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { createCommand, fetchBriefing, fetchMission, missionLogUrl, type DeskBriefing, type Mission, type MissionEvent } from "./lib/api";

const briefing = ref<DeskBriefing | null>(null);
const command = ref("Evaluate the OPC MVP delivery plan and return this week's action list.");
const mission = ref<Mission | null>(null);
const liveEvents = ref<MissionEvent[]>([]);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");
const socket = ref<WebSocket | null>(null);

const topAgent = computed(() => briefing.value?.team.find((agent) => agent.id === "ceo"));
const directReports = computed(() => briefing.value?.team.filter((agent) => agent.reportsTo === "coo") ?? []);

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
                <small>{{ agent.status }}</small>
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
              <p v-if="mission.resultText" class="result-text">{{ mission.resultText }}</p>
              <p v-else-if="mission.error" class="result-text error-text">{{ mission.error }}</p>
              <p v-else class="result-text">OpenClaw is processing this Founder Command.</p>
            </div>
            <div class="usage-grid">
              <span>{{ mission.usage.input }}</span>
              <span>{{ mission.usage.output }}</span>
              <span>{{ mission.usage.total }}</span>
              <small>input / output / total tokens</small>
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
  </main>
</template>
