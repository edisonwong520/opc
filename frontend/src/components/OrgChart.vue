<script setup lang="ts">
import { computed } from "vue";
import { VueFlow, type Edge, type Node } from "@vue-flow/core";
import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";

import type { ExecutiveAgent } from "../lib/api";

const props = defineProps<{
  agents: ExecutiveAgent[];
}>();

const emit = defineEmits<{
  edit: [];
}>();

const positions: Record<string, { x: number; y: number }> = {
  ceo: { x: 340, y: 20 },
  coo: { x: 340, y: 190 },
  cto: { x: 40, y: 380 },
  cfo: { x: 340, y: 380 },
  cmo: { x: 640, y: 380 },
  sre: { x: 940, y: 380 },
};

const nodes = computed<Node[]>(() =>
  props.agents.map((agent) => ({
    id: agent.id,
    type: "default",
    position: positions[agent.id] ?? { x: 40, y: 560 },
    data: {
      label: `${agent.name} | ${agent.title}`,
    },
    class: `org-node org-node-${agent.status}`,
  })),
);

const edges = computed<Edge[]>(() =>
  props.agents
    .filter((agent) => agent.reportsTo)
    .map((agent) => ({
      id: `${agent.reportsTo}-${agent.id}`,
      source: agent.reportsTo as string,
      target: agent.id,
      animated: agent.status === "ready",
    })),
);
</script>

<template>
  <section class="org-map">
    <button class="edit-team-btn" @click="emit('edit')">Edit Team</button>
    <div class="org-flow" aria-label="Executive team org chart">
      <VueFlow :nodes="nodes" :edges="edges" fit-view-on-init @node-click="emit('edit')" />
    </div>
  </section>
</template>
