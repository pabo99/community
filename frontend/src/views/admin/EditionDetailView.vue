<script setup lang="ts">
import Button from "primevue/button";
import Dialog from "primevue/dialog";
import ProgressSpinner from "primevue/progressspinner";
import { useToast } from "primevue/usetoast";
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { Edition, EditionUpdate, Program } from "@/api/admin";
import { deleteEdition, getEdition, getProgram, updateEdition } from "@/api/admin";
import { ApiError, errorDetail, parseValidationErrors } from "@/api/client";
import AdminBreadcrumb from "@/components/admin/AdminBreadcrumb.vue";
import EditionForm from "@/components/admin/EditionForm.vue";
import SourceTag from "@/components/admin/SourceTag.vue";
import StatusTag from "@/components/admin/StatusTag.vue";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const editionId = route.params.editionId as string;

const edition = ref<Edition | null>(null);
// The parent program, loaded for the breadcrumb trail (name, not UUID).
const program = ref<Program | null>(null);
const loading = ref(true);
const notFound = ref(false);
const loadError = ref(false);

const saving = ref(false);
const fieldErrors = ref<Record<string, string>>({});

const deleteDialog = ref(false);
const deletingEdition = ref(false);

// Discard-changes confirmation shown when Cancel is pressed with unsaved edits.
const discardDialog = ref(false);

async function load(): Promise<void> {
  loading.value = true;
  notFound.value = false;
  loadError.value = false;
  try {
    edition.value = await getEdition(editionId);
    // Best-effort: the breadcrumb degrades gracefully if the program lookup
    // fails, so a program error does not block editing the edition.
    try {
      program.value = await getProgram(edition.value.program_id);
    } catch {
      program.value = null;
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound.value = true;
    } else {
      loadError.value = true;
    }
  } finally {
    loading.value = false;
  }
}

async function onUpdate(payload: EditionUpdate): Promise<void> {
  saving.value = true;
  fieldErrors.value = {};
  try {
    edition.value = await updateEdition(editionId, payload);
    toast.add({ severity: "success", summary: "Edition updated", life: 3000 });
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      fieldErrors.value = parseValidationErrors(error.body);
      toast.add({
        severity: "error",
        summary: "Please fix the errors",
        detail: errorDetail(error.body, "Validation failed."),
        life: 5000,
      });
    } else {
      toast.add({ severity: "error", summary: "Could not update edition", life: 5000 });
    }
  } finally {
    saving.value = false;
  }
}

// Navigate back to the parent program detail (the natural "up" from an edition).
function goToProgram(): void {
  const programId = edition.value?.program_id;
  if (programId) {
    router.push({ name: "admin-program-detail", params: { programId } });
  } else {
    router.push({ name: "admin-programs" });
  }
}

// Cancel from the edit form. With unsaved changes, confirm before discarding;
// otherwise navigate straight to the parent program.
function onCancel(dirty: boolean): void {
  if (dirty) {
    discardDialog.value = true;
  } else {
    goToProgram();
  }
}

function confirmDiscard(): void {
  discardDialog.value = false;
  goToProgram();
}

async function onDeleteEdition(): Promise<void> {
  deletingEdition.value = true;
  try {
    await deleteEdition(editionId);
    toast.add({ severity: "success", summary: "Edition deleted", life: 3000 });
    deleteDialog.value = false;
    const programId = edition.value?.program_id;
    if (programId) {
      router.push({ name: "admin-program-detail", params: { programId } });
    } else {
      router.push({ name: "admin-programs" });
    }
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      toast.add({
        severity: "error",
        summary: "Cannot delete edition",
        detail: errorDetail(
          error.body,
          "This edition has projects, participants, or mentors. Remove them first.",
        ),
        life: 6000,
      });
    } else if (error instanceof ApiError && error.status === 404) {
      router.push({ name: "admin-programs" });
    } else {
      toast.add({ severity: "error", summary: "Could not delete edition", life: 5000 });
    }
  } finally {
    deletingEdition.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="flex flex-col gap-6">
    <div v-if="loading" class="flex justify-center py-12" aria-live="polite">
      <ProgressSpinner aria-label="Loading edition" />
    </div>

    <div v-else-if="notFound" class="flex flex-col items-start gap-3">
      <AdminBreadcrumb />
      <h1 class="text-2xl font-bold">Edition not found</h1>
    </div>

    <div v-else-if="loadError" class="flex flex-col items-start gap-3">
      <AdminBreadcrumb />
      <p class="text-red-600">Could not load this edition.</p>
      <Button label="Retry" icon="pi pi-refresh" severity="secondary" @click="load" />
    </div>

    <template v-else-if="edition">
      <AdminBreadcrumb
        :program="program ? { id: program.id, name: program.name } : undefined"
        :edition-slug="edition.slug"
      />

      <div class="flex items-start justify-between gap-4">
        <div class="flex flex-col gap-2">
          <h1 class="text-2xl font-bold">{{ edition.name }}</h1>
          <div class="flex flex-wrap items-center gap-3">
            <span class="font-mono text-surface-500">{{ edition.slug }}</span>
            <StatusTag :status="edition.status" />
            <SourceTag :source="edition.source" :external-id="edition.external_id" />
          </div>
          <p class="text-xs text-surface-500">
            Status is computed from the edition dates (UTC): upcoming, active, or finished.
          </p>
        </div>
        <Button
          icon="pi pi-trash"
          severity="danger"
          text
          :aria-label="`Delete ${edition.name}`"
          @click="deleteDialog = true"
        />
      </div>

      <div class="max-w-2xl">
        <EditionForm
          mode="edit"
          :edition="edition"
          :submitting="saving"
          :field-errors="fieldErrors"
          @submit-update="onUpdate"
          @cancel="onCancel"
        />
      </div>

      <Dialog
        v-model:visible="deleteDialog"
        modal
        header="Delete edition"
        :style="{ width: '28rem' }"
        :closable="!deletingEdition"
      >
        <p class="text-surface-700 dark:text-surface-200">
          Delete <span class="font-semibold">{{ edition.name }}</span
          >? This cannot be undone. An edition can only be deleted when it has no projects,
          participants, or mentors.
        </p>
        <template #footer>
          <Button
            label="Cancel"
            severity="secondary"
            text
            :disabled="deletingEdition"
            @click="deleteDialog = false"
          />
          <Button
            label="Delete"
            icon="pi pi-trash"
            severity="danger"
            :loading="deletingEdition"
            @click="onDeleteEdition"
          />
        </template>
      </Dialog>

      <Dialog
        v-model:visible="discardDialog"
        modal
        header="Discard changes?"
        :style="{ width: '28rem' }"
      >
        <p class="text-surface-700 dark:text-surface-200">
          You have unsaved changes. Leave this edition and discard them?
        </p>
        <template #footer>
          <Button label="Keep editing" severity="secondary" text @click="discardDialog = false" />
          <Button label="Discard changes" severity="danger" @click="confirmDiscard" />
        </template>
      </Dialog>
    </template>
  </section>
</template>
