<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { createCommand, fetchBriefing, type CommandPlan, type DeskBriefing } from "./lib/api";

const briefing = ref<DeskBriefing | null>(null);
const command = ref("帮我评估 CEO Desk 的 MVP 交付计划，并给出本周行动清单。");
const commandPlan = ref<CommandPlan | null>(null);
const loading = ref(true);
const submitting = ref(false);
const error = ref("");

const topAgent = computed(() => briefing.value?.team.find((agent) => agent.id === "ceo"));
const directReports = computed(() => briefing.value?.team.filter((agent) => agent.reportsTo === "coo") ?? []);

async function loadBriefing() {
  try {
    loading.value = true;
    briefing.value = await fetchBriefing();
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "CEO Desk 暂时无法连接。";
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
    commandPlan.value = await createCommand(command.value.trim());
  } catch (caught) {
    error.value = caught instanceof Error ? caught.message : "指令规划失败。";
  } finally {
    submitting.value = false;
  }
}

onMounted(loadBriefing);
</script>

<template>
  <main class="min-h-screen bg-[#eef2ef] text-[#171717]">
    <section class="workspace-grid min-h-screen px-5 py-5 sm:px-8 lg:px-10">
      <aside class="command-rail">
        <p class="eyebrow">OpenClaw Executive OS</p>
        <h1>CEO Desk</h1>
        <p class="lede">把一句战略指令交给一支 AI 高管团队，让 COO 拆解，CTO/CFO/CMO 并行推进，CEO 收口汇报。</p>

        <form class="command-box" @submit.prevent="submitCommand">
          <label for="command">CEO Command</label>
          <textarea id="command" v-model="command" rows="7" />
          <button type="submit" :disabled="submitting">
            {{ submitting ? "规划中..." : "分配给高管团队" }}
          </button>
        </form>

        <div v-if="commandPlan" class="dispatch">
          <p class="dispatch-title">{{ commandPlan.status }}</p>
          <p>{{ commandPlan.nextStep }}</p>
          <ul>
            <li v-for="workstream in commandPlan.workstreams" :key="workstream.agent">
              <strong>{{ workstream.agent }}</strong>
              <span>{{ workstream.task }}</span>
            </li>
          </ul>
        </div>
      </aside>

      <section class="board">
        <div v-if="loading" class="notice">正在连接 CEO Desk API...</div>
        <div v-else-if="error" class="notice error">{{ error }}</div>

        <template v-else-if="briefing">
          <header class="board-header">
            <div>
              <p class="eyebrow">Mission Control</p>
              <h2>{{ briefing.positioning }}</h2>
            </div>
            <div class="runtime">
              <span>{{ briefing.runtime }}</span>
              <small>{{ briefing.gateway }}</small>
            </div>
          </header>

          <section class="metrics" aria-label="CEO Desk metrics">
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
        </template>
      </section>
    </section>
  </main>
</template>
