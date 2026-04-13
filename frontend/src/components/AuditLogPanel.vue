<script setup lang="ts">
import { onMounted, ref } from "vue";

import { fetchAuditLogs, type AuditLogEntry } from "../lib/api";

const emit = defineEmits<{
  error: [message: string];
}>();

const logs = ref<AuditLogEntry[]>([]);
const action = ref("");
const loading = ref(false);

async function loadLogs() {
  try {
    loading.value = true;
    const result = await fetchAuditLogs({ action: action.value, limit: 50 });
    logs.value = result.logs;
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Audit log unavailable.");
  } finally {
    loading.value = false;
  }
}

onMounted(loadLogs);
</script>

<template>
  <section class="audit-log-panel">
    <div class="audit-header">
      <h2>Audit Log</h2>
      <div>
        <input v-model="action" placeholder="Filter action" @keyup.enter="loadLogs" />
        <button @click="loadLogs" :disabled="loading">{{ loading ? "Loading..." : "Load" }}</button>
      </div>
    </div>
    <div class="audit-list">
      <article v-for="log in logs" :key="log.id">
        <strong>{{ log.action }}</strong>
        <span>{{ log.entityType }} {{ log.entityId }}</span>
        <small>{{ log.actor }} · {{ new Date(log.createdAt).toLocaleString() }}</small>
      </article>
    </div>
  </section>
</template>
