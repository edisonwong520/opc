<script setup lang="ts">
import { ref } from "vue";

import { bootstrapFounder, login, logout, type SessionInfo } from "../lib/api";

const props = defineProps<{
  session: SessionInfo | null;
}>();

const emit = defineEmits<{
  changed: [session: SessionInfo];
  error: [message: string];
}>();

const username = ref("");
const password = ref("");
const organizationName = ref("Default OPC");
const working = ref(false);

async function handleLogin() {
  try {
    working.value = true;
    emit("changed", await login(username.value, password.value));
    password.value = "";
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Sign in failed.");
  } finally {
    working.value = false;
  }
}

async function handleBootstrap() {
  try {
    working.value = true;
    emit("changed", await bootstrapFounder(username.value, password.value, organizationName.value));
    password.value = "";
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Founder setup failed.");
  } finally {
    working.value = false;
  }
}

async function handleLogout() {
  try {
    working.value = true;
    emit("changed", await logout());
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Sign out failed.");
  } finally {
    working.value = false;
  }
}
</script>

<template>
  <section class="auth-panel">
    <template v-if="props.session?.authenticated">
      <span>{{ props.session.username }}</span>
      <small>{{ props.session.organization.name }} · {{ props.session.role }}</small>
      <button @click="handleLogout" :disabled="working">Sign Out</button>
    </template>
    <template v-else>
      <input v-model="username" placeholder="Username" />
      <input v-model="password" type="password" placeholder="Password" />
      <input v-model="organizationName" placeholder="Organization" />
      <div>
        <button @click="handleLogin" :disabled="working">Sign In</button>
        <button @click="handleBootstrap" :disabled="working">First Founder</button>
      </div>
    </template>
  </section>
</template>
