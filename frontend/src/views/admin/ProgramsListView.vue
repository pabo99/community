<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import ProgressSpinner from "primevue/progressspinner";
import { useToast } from "primevue/usetoast";
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import type { ProgramCreate, ProgramListItem } from "@/api/admin";
import { createProgram, deleteProgram, listPrograms } from "@/api/admin";
import { ApiError, errorDetail, parseValidationErrors } from "@/api/client";
import AdminBreadcrumb from "@/components/admin/AdminBreadcrumb.vue";
import ProgramForm from "@/components/admin/ProgramForm.vue";

const router = useRouter();
const toast = useToast();

const programs = ref<ProgramListItem[]>([]);
const loading = ref(true);
const loadError = ref(false);

const dialogVisible = ref(false);
const submitting = ref(false);
const fieldErrors = ref<Record<string, string>>({});

// Delete confirmation state. Deletion is permitted only when the program has no
// editions; the backend enforces this and returns 409 otherwise.
const deleteTarget = ref<ProgramListItem | null>(null);
const deleting = ref(false);

async function load(): Promise<void> {
  loading.value = true;
  loadError.value = false;
  try {
    programs.value = await listPrograms();
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

function openCreate(): void {
  fieldErrors.value = {};
  dialogVisible.value = true;
}

async function onCreate(payload: ProgramCreate): Promise<void> {
  submitting.value = true;
  fieldErrors.value = {};
  try {
    const created = await createProgram(payload);
    toast.add({ severity: "success", summary: "Program created", life: 3000 });
    dialogVisible.value = false;
    router.push({ name: "admin-program-detail", params: { programId: created.id } });
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      fieldErrors.value = parseValidationErrors(error.body);
    } else if (error instanceof ApiError && error.status === 409) {
      toast.add({
        severity: "error",
        summary: "Conflict",
        detail: errorDetail(error.body, "A program with this name already exists."),
        life: 5000,
      });
    } else {
      toast.add({ severity: "error", summary: "Could not create program", life: 5000 });
    }
  } finally {
    submitting.value = false;
  }
}

function manage(program: ProgramListItem): void {
  router.push({ name: "admin-program-detail", params: { programId: program.id } });
}

function confirmDelete(program: ProgramListItem): void {
  // Empty-only deletion: do not open the confirmation flow for a non-empty
  // program (the button is also disabled in that case). Backend stays
  // authoritative regardless.
  if (program.edition_count > 0) return;
  deleteTarget.value = program;
}

async function onDelete(): Promise<void> {
  const target = deleteTarget.value;
  if (!target) return;
  deleting.value = true;
  try {
    await deleteProgram(target.id);
    toast.add({ severity: "success", summary: "Program deleted", life: 3000 });
    deleteTarget.value = null;
    await load();
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      toast.add({
        severity: "error",
        summary: "Cannot delete program",
        detail: errorDetail(error.body, "This program still has editions. Delete them first."),
        life: 6000,
      });
    } else if (error instanceof ApiError && error.status === 404) {
      toast.add({ severity: "warn", summary: "Program no longer exists", life: 4000 });
      deleteTarget.value = null;
      await load();
    } else {
      toast.add({ severity: "error", summary: "Could not delete program", life: 5000 });
    }
  } finally {
    deleting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="flex flex-col gap-6">
    <AdminBreadcrumb />

    <div class="flex items-center justify-between gap-4">
      <div class="flex flex-col gap-1">
        <h1 class="text-2xl font-bold">Programs</h1>
        <p class="text-surface-600 dark:text-surface-300">Manage programs and their editions.</p>
      </div>
      <Button label="New program" icon="pi pi-plus" @click="openCreate" />
    </div>

    <div v-if="loading" class="flex justify-center py-12" aria-live="polite">
      <ProgressSpinner aria-label="Loading programs" />
    </div>

    <div v-else-if="loadError" class="flex flex-col items-start gap-3">
      <p class="text-red-600">Could not load programs.</p>
      <Button label="Retry" icon="pi pi-refresh" severity="secondary" @click="load" />
    </div>

    <div
      v-else-if="programs.length === 0"
      class="rounded-lg border border-dashed border-surface-300 p-10 text-center dark:border-surface-700"
    >
      <p class="text-surface-600 dark:text-surface-300">No programs yet.</p>
      <Button
        class="mt-4"
        label="Create your first program"
        icon="pi pi-plus"
        @click="openCreate"
      />
    </div>

    <DataTable
      v-else
      :value="programs"
      data-key="id"
      selection-mode="single"
      :row-hover="true"
      @row-click="manage($event.data)"
    >
      <Column header="" style="width: 3rem">
        <template #body="{ data }">
          <i :class="`pi pi-${data.icon}`" :aria-label="`Icon: ${data.icon}`"></i>
        </template>
      </Column>
      <Column field="name" header="Program" sortable />
      <Column header="Editions">
        <template #body="{ data }">{{ data.edition_count }}</template>
      </Column>
      <Column header="Active edition(s)">
        <template #body="{ data }">
          <span v-if="data.active_editions.length === 0" class="text-surface-400">—</span>
          <span v-else class="flex flex-wrap gap-1">
            <span
              v-for="active in data.active_editions"
              :key="active.id"
              class="rounded bg-surface-100 px-2 py-0.5 text-xs dark:bg-surface-800"
            >
              {{ active.slug }}
            </span>
          </span>
        </template>
      </Column>
      <Column header="" style="width: 11rem">
        <template #body="{ data }">
          <div class="flex items-center justify-end gap-1">
            <Button
              label="Manage"
              icon="pi pi-cog"
              severity="secondary"
              text
              @click.stop="manage(data)"
            />
            <!-- Deletion is empty-only. Disable (don't just fail) when the
                 program still has editions so the user never enters a flow that
                 is guaranteed to 409. The backend remains authoritative. -->
            <Button
              icon="pi pi-trash"
              severity="danger"
              text
              rounded
              :disabled="data.edition_count > 0"
              :aria-label="
                data.edition_count > 0
                  ? `Cannot delete ${data.name}: remove its editions first`
                  : `Delete ${data.name}`
              "
              :title="
                data.edition_count > 0
                  ? 'Remove all editions before deleting this program.'
                  : 'Delete program'
              "
              @click.stop="confirmDelete(data)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="dialogVisible"
      modal
      header="New program"
      :style="{ width: '32rem' }"
      :dismissable-mask="true"
    >
      <ProgramForm
        mode="create"
        :submitting="submitting"
        :field-errors="fieldErrors"
        @submit-create="onCreate"
        @cancel="dialogVisible = false"
      />
    </Dialog>

    <Dialog
      :visible="deleteTarget !== null"
      modal
      header="Delete program"
      :style="{ width: '28rem' }"
      :closable="!deleting"
      @update:visible="(open: boolean) => !open && (deleteTarget = null)"
    >
      <p class="text-surface-700 dark:text-surface-200">
        Delete <span class="font-semibold">{{ deleteTarget?.name }}</span
        >? This cannot be undone. A program can only be deleted when it has no editions.
      </p>
      <template #footer>
        <Button
          label="Cancel"
          severity="secondary"
          text
          :disabled="deleting"
          @click="deleteTarget = null"
        />
        <Button
          label="Delete"
          icon="pi pi-trash"
          severity="danger"
          :loading="deleting"
          @click="onDelete"
        />
      </template>
    </Dialog>
  </section>
</template>
