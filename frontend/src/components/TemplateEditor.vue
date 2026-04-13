<script setup lang="ts">
import { onMounted, ref } from "vue";

import {
  createTemplate,
  deleteTemplate,
  fetchTemplates,
  updateTemplate,
  type ExecutiveAgent,
  type TemplateInput,
} from "../lib/api";

const emit = defineEmits<{
  close: [];
  saved: [];
  error: [message: string];
}>();

const templates = ref<ExecutiveAgent[]>([]);
const showTemplateForm = ref(false);
const editingTemplate = ref<ExecutiveAgent | null>(null);
const editForm = ref<TemplateInput>({ id: "", name: "" });
const toolsText = ref("");
const savingTemplate = ref(false);

async function loadTemplates() {
  try {
    const result = await fetchTemplates();
    templates.value = result.templates;
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Failed to load templates.");
  }
}

function startCreate() {
  editingTemplate.value = null;
  showTemplateForm.value = true;
  toolsText.value = "";
  editForm.value = {
    id: "",
    name: "",
    title: "",
    mission: "",
    reportsTo: "coo",
    status: "ready",
    tools: [],
    modelPreference: "",
    budgetLimitUsd: 0,
  };
}

function startEdit(template: ExecutiveAgent) {
  editingTemplate.value = template;
  showTemplateForm.value = true;
  toolsText.value = template.tools.join(", ");
  editForm.value = {
    id: template.id,
    name: template.name,
    title: template.title,
    mission: template.mission,
    reportsTo: template.reportsTo ?? "",
    status: template.status,
    tools: [...template.tools],
    modelPreference: template.modelPreference,
    budgetLimitUsd: parseFloat(template.budgetLimitUsd) || 0,
  };
}

function cancelEdit() {
  editingTemplate.value = null;
  showTemplateForm.value = false;
  toolsText.value = "";
  editForm.value = { id: "", name: "" };
}

async function saveTemplate() {
  try {
    savingTemplate.value = true;
    const payload = {
      ...editForm.value,
      tools: toolsText.value
        .split(",")
        .map((tool) => tool.trim())
        .filter(Boolean),
    };
    if (editingTemplate.value) {
      await updateTemplate(editingTemplate.value.id, payload);
    } else {
      await createTemplate(payload);
    }
    await loadTemplates();
    cancelEdit();
    emit("saved");
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Failed to save template.");
  } finally {
    savingTemplate.value = false;
  }
}

async function removeTemplate(id: string) {
  try {
    await deleteTemplate(id);
    await loadTemplates();
    emit("saved");
  } catch (caught) {
    emit("error", caught instanceof Error ? caught.message : "Failed to delete template.");
  }
}

onMounted(loadTemplates);
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <header class="modal-header">
        <h2>Agent Templates</h2>
        <button class="close-btn" @click="emit('close')">x</button>
      </header>
      <div class="modal-body">
        <div v-if="showTemplateForm" class="edit-form">
          <label>ID</label>
          <input v-model="editForm.id" :disabled="Boolean(editingTemplate)" />
          <label>Name</label>
          <input v-model="editForm.name" />
          <label>Title</label>
          <input v-model="editForm.title" />
          <label>Mission</label>
          <textarea v-model="editForm.mission" rows="3" />
          <label>Reports To</label>
          <input v-model="editForm.reportsTo" />
          <label>Status</label>
          <select v-model="editForm.status">
            <option value="ready">Ready</option>
            <option value="standby">Standby</option>
            <option value="disabled">Disabled</option>
          </select>
          <label>Tools</label>
          <input v-model="toolsText" placeholder="browser, shell, docs" />
          <label>Model Preference</label>
          <input v-model="editForm.modelPreference" placeholder="provider/model" />
          <label>Budget Limit (USD)</label>
          <input v-model.number="editForm.budgetLimitUsd" type="number" step="0.01" />
          <div class="form-actions">
            <button class="save-btn" @click="saveTemplate" :disabled="savingTemplate">{{ savingTemplate ? "Saving..." : "Save" }}</button>
            <button class="cancel-btn" @click="cancelEdit">Cancel</button>
          </div>
        </div>
        <div v-else class="template-list">
          <button class="new-template-btn" @click="startCreate">New Template</button>
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
</template>
