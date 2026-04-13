<script setup lang="ts">
import { onMounted, ref } from "vue";

import { createInvitation, fetchInvitations, revokeInvitation, type Invitation, type SessionInfo } from "../lib/api";

const props = defineProps<{
  session: SessionInfo | null;
}>();

const emit = defineEmits<{
  error: [message: string];
}>();

const invitations = ref<Invitation[]>([]);
const email = ref("");
const role = ref("operator");
const working = ref(false);
const loading = ref(false);

const canManage = props.session?.role === "admin" || props.session?.role === "founder";

async function loadInvitations() {
  if (!canManage) return;
  try {
    loading.value = true;
    const result = await fetchInvitations();
    invitations.value = result.invitations;
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Unable to load invitations.");
  } finally {
    loading.value = false;
  }
}

async function handleCreate() {
  if (!email.value.trim()) return;
  try {
    working.value = true;
    await createInvitation(email.value.trim().toLowerCase(), role.value);
    email.value = "";
    await loadInvitations();
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Unable to create invitation.");
  } finally {
    working.value = false;
  }
}

async function handleRevoke(invitationId: string) {
  try {
    working.value = true;
    await revokeInvitation(invitationId);
    await loadInvitations();
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Unable to revoke invitation.");
  } finally {
    working.value = false;
  }
}

function formatExpires(expiresAt: string): string {
  const date = new Date(expiresAt);
  const now = new Date();
  const days = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 0) return "Expired";
  if (days === 1) return "Expires tomorrow";
  return `Expires in ${days} days`;
}

onMounted(() => {
  void loadInvitations();
});
</script>

<template>
  <section v-if="canManage" class="invitation-panel">
    <h3>Team Invitations</h3>
    <div class="invitation-form">
      <input v-model="email" type="email" placeholder="Email address" />
      <select v-model="role">
        <option value="operator">Operator</option>
        <option value="viewer">Viewer</option>
        <option value="founder">Founder</option>
        <option value="admin">Admin</option>
      </select>
      <button @click="handleCreate" :disabled="working || !email.trim()">
        {{ working ? "Sending..." : "Invite" }}
      </button>
    </div>
    <div v-if="loading" class="notice">Loading invitations...</div>
    <div v-else-if="invitations.length === 0" class="notice">No pending invitations.</div>
    <ul v-else class="invitation-list">
      <li v-for="inv in invitations" :key="inv.id">
        <span>{{ inv.email }}</span>
        <small>{{ inv.role }} · {{ formatExpires(inv.expiresAt) }}</small>
        <button @click="handleRevoke(inv.id)" :disabled="working">Revoke</button>
      </li>
    </ul>
  </section>
</template>