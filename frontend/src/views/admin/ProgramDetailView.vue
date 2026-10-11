<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { Edition, EditionCreate, Program, ProgramIcon, ProgramUpdate } from "@/api/admin";
import {
  createEdition,
  deleteEdition,
  deleteProgram,
  getProgram,
  listEditions,
  PROGRAM_ICONS,
  updateProgram,
} from "@/api/admin";
import { ApiError, errorDetail, parseValidationErrors } from "@/api/client";
import AdminBreadcrumb from "@/components/admin/AdminBreadcrumb.vue";
import EditionForm from "@/components/admin/EditionForm.vue";
import StatusTag from "@/components/admin/StatusTag.vue";

const route = useRoute();
const router = useRouter();
const toast = useToast();

const programId = route.params.programId as string;

const program = ref<Program | null>(null);
const editions = ref<Edition[]>([]);
const loading = ref(true);
const notFound = ref(false);
const loadError = ref(false);

// The program form is permanently visible. It is read-only until the user
// clicks Edit; Save persists changes, Cancel discards them and restores the
// last-saved values. The slug is immutable and shown read-only in both modes.
const editing = ref(false);
const savingProgram = ref(false);
const programErrors = ref<Record<string, string>>({});

const iconOptions = PROGRAM_ICONS.map((icon) => ({ label: icon, value: icon }));

const form = reactive({
  name: "",
  description: "",
  icon: "folder" as ProgramIcon,
});

// Snapshot the persisted program into the editable form. Called on load, after
// a successful save, and on Cancel so the form always reflects saved state.
function resetForm(): void {
  if (!program.value) return;
  form.name = program.value.name;
  form.description = program.value.description ?? "";
  form.icon = program.value.icon;
  programErrors.value = {};
}

const editionDialog = ref(false);
const creatingEdition = ref(false);
const editionErrors = ref<Record<string, string>>({});

const deleteDialog = ref(false);
const deletingProgram = ref(false);

// Per-row edition deletion. Deletion is empty-only (no projects/participants/
// mentors); the backend enforces this and returns 409 otherwise.
const editionDeleteTarget = ref<Edition | null>(null);
const deletingEdition = ref(false);

async function load(): Promise<void> {
  loading.value = true;
  notFound.value = false;
  loadError.value = false;
  try {
    program.value = await getProgram(programId);
    editions.value = await listEditions(programId);
    resetForm();
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

function startEdit(): void {
  resetForm();
  editing.value = true;
}

function cancelEdit(): void {
  // Restore the last-saved values and leave edit mode.
  resetForm();
  editing.value = false;
}

async function saveProgram(): Promise<void> {
  programErrors.value = {};
  if (!form.name.trim()) {
    programErrors.value.name = "Name is required.";
    return;
  }
  savingProgram.value = true;
  const payload: ProgramUpdate = {
    name: form.name.trim(),
    description: form.description.trim() ? form.description.trim() : null,
    icon: form.icon,
  };
  try {
    program.value = await updateProgram(programId, payload);
    resetForm();
    editing.value = false;
    toast.add({ severity: "success", summary: "Program updated", life: 3000 });
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      programErrors.value = parseValidationErrors(error.body);
    } else {
      toast.add({ severity: "error", summary: "Could not update program", life: 5000 });
    }
  } finally {
    savingProgram.value = false;
  }
}

function programErr(field: string): string | undefined {
  return programErrors.value[field];
}

function openEditionDialog(): void {
  editionErrors.value = {};
  editionDialog.value = true;
}

async function onCreateEdition(payload: EditionCreate): Promise<void> {
  creatingEdition.value = true;
  editionErrors.value = {};
  try {
    const created = await createEdition(programId, payload);
    toast.add({ severity: "success", summary: "Edition created", life: 3000 });
    editionDialog.value = false;
    router.push({ name: "admin-edition-detail", params: { editionId: created.id } });
  } catch (error) {
    if (error instanceof ApiError && error.status === 422) {
      editionErrors.value = parseValidationErrors(error.body);
    } else if (error instanceof ApiError && error.status === 409) {
      toast.add({
        severity: "error",
        summary: "Conflict",
        detail: errorDetail(error.body, "An edition for this period already exists."),
        life: 5000,
      });
    } else {
      toast.add({ severity: "error", summary: "Could not create edition", life: 5000 });
    }
  } finally {
    creatingEdition.value = false;
  }
}

function openEdition(edition: Edition): void {
  router.push({ name: "admin-edition-detail", params: { editionId: edition.id } });
}

function confirmDeleteEdition(edition: Edition): void {
  editionDeleteTarget.value = edition;
}

async function onDeleteEdition(): Promise<void> {
  const target = editionDeleteTarget.value;
  if (!target) return;
  deletingEdition.value = true;
  try {
    await deleteEdition(target.id);
    toast.add({ severity: "success", summary: "Edition deleted", life: 3000 });
    editionDeleteTarget.value = null;
    // Refresh the editions table (and program, so the delete-guard stays correct).
    await load();
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
      toast.add({ severity: "warn", summary: "Edition no longer exists", life: 4000 });
      editionDeleteTarget.value = null;
      await load();
    } else {
      toast.add({ severity: "error", summary: "Could not delete edition", life: 5000 });
    }
  } finally {
    deletingEdition.value = false;
  }
}

function openProgramDelete(): void {
  // Empty-only deletion: never open the confirmation for a non-empty program
  // (the button is also disabled). Backend stays authoritative regardless.
  if (editions.value.length > 0) return;
  deleteDialog.value = true;
}

async function onDeleteProgram(): Promise<void> {
  deletingProgram.value = true;
  try {
    await deleteProgram(programId);
    toast.add({ severity: "success", summary: "Program deleted", life: 3000 });
    deleteDialog.value = false;
    router.push({ name: "admin-programs" });
  } catch (error) {
    if (error instanceof ApiError && error.status === 409) {
      toast.add({
        severity: "error",
        summary: "Cannot delete program",
        detail: errorDetail(error.body, "This program still has editions. Delete them first."),
        life: 6000,
      });
    } else if (error instanceof ApiError && error.status === 404) {
      router.push({ name: "admin-programs" });
    } else {
      toast.add({ severity: "error", summary: "Could not delete program", life: 5000 });
    }
  } finally {
    deletingProgram.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="flex flex-col gap-6">
    <div v-if="loading" class="flex justify-center py-12" aria-live="polite">
      <ProgressSpinner aria-label="Loading program" />
    </div>

    <div v-else-if="notFound" class="flex flex-col items-start gap-3">
      <AdminBreadcrumb />
      <h1 class="text-2xl font-bold">Program not found</h1>
    </div>

    <div v-else-if="loadError" class="flex flex-col items-start gap-3">
      <AdminBreadcrumb />
      <p class="text-red-600">Could not load this program.</p>
      <Button label="Retry" icon="pi pi-refresh" severity="secondary" @click="load" />
    </div>

    <template v-else-if="program">
      <AdminBreadcrumb :program="{ id: program.id, name: program.name }" />

      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3">
          <i :class="`pi pi-${program.icon}`" class="text-2xl" aria-hidden="true"></i>
          <h1 class="text-2xl font-bold">{{ program.name }}</h1>
        </div>
        <div class="flex flex-col items-end gap-1">
          <div class="flex items-center gap-2">
            <Button
              v-if="!editing"
              label="Edit"
              icon="pi pi-pencil"
              severity="secondary"
              @click="startEdit"
            />
            <!-- Deletion is empty-only. Disable while the program still has
                 editions so the user never enters a guaranteed-to-409 flow.
                 The backend remains authoritative. -->
            <Button
              label="Delete"
              icon="pi pi-trash"
              severity="danger"
              text
              :disabled="editions.length > 0"
              :aria-label="
                editions.length > 0
                  ? `Cannot delete ${program.name}: remove its editions first`
                  : `Delete ${program.name}`
              "
              @click="openProgramDelete"
            />
          </div>
          <small v-if="editions.length > 0" class="text-surface-500">
            Remove all editions before deleting this program.
          </small>
        </div>
      </div>

      <!-- Permanent program form: read-only until Edit, then editable in place.
           Responsive 12-column grid: icon (2) + name (5) + identifier (5) on
           wide screens, description full width; everything stacks on mobile. -->
      <form class="flex flex-col gap-5" @submit.prevent="saveProgram">
        <div class="grid grid-cols-1 gap-5 md:grid-cols-12">
          <!-- Icon: 2 of 12 columns, with a large square preview/selector. -->
          <div class="flex flex-col gap-1 md:col-span-2">
            <label for="program-icon" class="text-sm font-medium">Icon</label>
            <div
              class="flex aspect-square w-full max-w-[7rem] items-center justify-center rounded-lg border border-surface-200 bg-surface-50 dark:border-surface-700 dark:bg-surface-900"
            >
              <i :class="`pi pi-${form.icon} text-4xl`" aria-hidden="true"></i>
            </div>
            <Select
              v-if="editing"
              id="program-icon"
              v-model="form.icon"
              :options="iconOptions"
              option-label="label"
              option-value="value"
              class="mt-1 w-full max-w-[7rem]"
            >
              <template #value="{ value }">
                <span class="inline-flex items-center gap-2">
                  <i :class="`pi pi-${value}`" aria-hidden="true"></i> {{ value }}
                </span>
              </template>
              <template #option="{ option }">
                <span class="inline-flex items-center gap-2">
                  <i :class="`pi pi-${option.value}`" aria-hidden="true"></i> {{ option.label }}
                </span>
              </template>
            </Select>
          </div>

          <!-- Name: 5 of 12 columns. -->
          <div class="flex flex-col gap-1 md:col-span-5">
            <label for="program-name" class="text-sm font-medium">Name</label>
            <InputText
              id="program-name"
              v-model="form.name"
              :readonly="!editing"
              :invalid="!!programErr('name')"
              :class="!editing ? 'pointer-events-none bg-surface-50 dark:bg-surface-900' : ''"
            />
            <Message v-if="programErr('name')" severity="error" size="small" variant="simple">
              {{ programErr("name") }}
            </Message>
          </div>

          <!-- Identifier (slug): 5 of 12 columns, always immutable. -->
          <div class="flex flex-col gap-1 md:col-span-5">
            <label for="program-slug" class="text-sm font-medium">Identifier (slug)</label>
            <InputText
              id="program-slug"
              :model-value="program.slug"
              readonly
              class="pointer-events-none bg-surface-50 font-mono dark:bg-surface-900"
            />
            <small class="text-surface-500">The slug is permanent and cannot be changed.</small>
          </div>

          <!-- Description: full width (12 columns). -->
          <div class="flex flex-col gap-1 md:col-span-12">
            <label for="program-description" class="text-sm font-medium">Description</label>
            <Textarea
              id="program-description"
              v-model="form.description"
              rows="3"
              auto-resize
              :readonly="!editing"
              :placeholder="!editing && !form.description ? 'No description.' : ''"
              :class="!editing ? 'pointer-events-none bg-surface-50 dark:bg-surface-900' : ''"
            />
          </div>
        </div>

        <div v-if="editing" class="flex justify-end gap-2">
          <Button
            type="button"
            label="Cancel"
            severity="secondary"
            text
            :disabled="savingProgram"
            @click="cancelEdit"
          />
          <Button type="submit" label="Save changes" :loading="savingProgram" />
        </div>
      </form>

      <!-- Editions table, immediately below the program form (full width). -->
      <div
        class="flex items-center justify-between gap-4 border-t border-surface-200 pt-6 dark:border-surface-800"
      >
        <h2 class="text-xl font-semibold">Editions</h2>
        <Button label="New edition" icon="pi pi-plus" @click="openEditionDialog" />
      </div>

      <div
        v-if="editions.length === 0"
        class="rounded-lg border border-dashed border-surface-300 p-10 text-center dark:border-surface-700"
      >
        <p class="text-surface-600 dark:text-surface-300">This program has no editions yet.</p>
        <Button
          class="mt-4"
          label="Create an edition"
          icon="pi pi-plus"
          @click="openEditionDialog"
        />
      </div>

      <DataTable
        v-else
        :value="editions"
        data-key="id"
        selection-mode="single"
        :row-hover="true"
        @row-click="openEdition($event.data)"
      >
        <Column field="slug" header="Period" sortable />
        <Column field="name" header="Name" sortable />
        <Column header="Status">
          <template #body="{ data }"><StatusTag :status="data.status" /></template>
        </Column>
        <Column header="Dates">
          <template #body="{ data }">
            <span class="text-sm text-surface-600 dark:text-surface-300">
              {{ data.starts_on }} → {{ data.ends_on }}
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
                @click.stop="openEdition(data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text
                rounded
                :aria-label="`Delete ${data.name}`"
                @click.stop="confirmDeleteEdition(data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <Dialog
        v-model:visible="editionDialog"
        modal
        header="New edition"
        :style="{ width: '36rem' }"
        :dismissable-mask="true"
      >
        <EditionForm
          mode="create"
          :submitting="creatingEdition"
          :field-errors="editionErrors"
          @submit-create="onCreateEdition"
          @cancel="editionDialog = false"
        />
      </Dialog>

      <Dialog
        v-model:visible="deleteDialog"
        modal
        header="Delete program"
        :style="{ width: '28rem' }"
        :closable="!deletingProgram"
      >
        <p class="text-surface-700 dark:text-surface-200">
          Delete <span class="font-semibold">{{ program.name }}</span
          >? This cannot be undone. A program can only be deleted when it has no editions.
        </p>
        <template #footer>
          <Button
            label="Cancel"
            severity="secondary"
            text
            :disabled="deletingProgram"
            @click="deleteDialog = false"
          />
          <Button
            label="Delete"
            icon="pi pi-trash"
            severity="danger"
            :loading="deletingProgram"
            @click="onDeleteProgram"
          />
        </template>
      </Dialog>

      <Dialog
        :visible="editionDeleteTarget !== null"
        modal
        header="Delete edition"
        :style="{ width: '28rem' }"
        :closable="!deletingEdition"
        @update:visible="(open: boolean) => !open && (editionDeleteTarget = null)"
      >
        <p class="text-surface-700 dark:text-surface-200">
          Delete <span class="font-semibold">{{ editionDeleteTarget?.name }}</span
          >? This cannot be undone. An edition can only be deleted when it has no projects,
          participants, or mentors.
        </p>
        <template #footer>
          <Button
            label="Cancel"
            severity="secondary"
            text
            :disabled="deletingEdition"
            @click="editionDeleteTarget = null"
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
    </template>
  </section>
</template>
