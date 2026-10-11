<script setup lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { reactive, ref } from "vue";

import type { Program, ProgramCreate, ProgramIcon, ProgramUpdate } from "@/api/admin";
import { PROGRAM_ICONS } from "@/api/admin";

const props = defineProps<{
  mode: "create" | "edit";
  program?: Program;
  submitting?: boolean;
  fieldErrors?: Record<string, string>;
}>();

const emit = defineEmits<{
  (e: "submit-create", payload: ProgramCreate): void;
  (e: "submit-update", payload: ProgramUpdate): void;
  (e: "cancel"): void;
}>();

const iconOptions = PROGRAM_ICONS.map((icon) => ({ label: icon, value: icon }));

const form = reactive({
  name: props.program?.name ?? "",
  description: props.program?.description ?? "",
  icon: (props.program?.icon ?? "folder") as ProgramIcon,
});

const localErrors = ref<Record<string, string>>({});

function err(field: string): string | undefined {
  return localErrors.value[field] ?? props.fieldErrors?.[field];
}

function submit(): void {
  localErrors.value = {};
  if (!form.name.trim()) {
    localErrors.value.name = "Name is required.";
    return;
  }
  const description = form.description.trim() ? form.description.trim() : null;
  if (props.mode === "create") {
    emit("submit-create", { name: form.name.trim(), description, icon: form.icon });
  } else {
    emit("submit-update", { name: form.name.trim(), description, icon: form.icon });
  }
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="submit">
    <div class="flex flex-col gap-1">
      <label for="program-name" class="text-sm font-medium">Name</label>
      <InputText id="program-name" v-model="form.name" :invalid="!!err('name')" />
      <small class="text-surface-500">
        The URL identifier (slug) is generated automatically from the name.
      </small>
      <Message v-if="err('name')" severity="error" size="small" variant="simple">
        {{ err("name") }}
      </Message>
    </div>

    <div class="flex flex-col gap-1">
      <label for="program-icon" class="text-sm font-medium">Icon</label>
      <Select
        id="program-icon"
        v-model="form.icon"
        :options="iconOptions"
        option-label="label"
        option-value="value"
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
      <Message v-if="err('icon')" severity="error" size="small" variant="simple">
        {{ err("icon") }}
      </Message>
    </div>

    <div class="flex flex-col gap-1">
      <label for="program-description" class="text-sm font-medium">Description</label>
      <Textarea id="program-description" v-model="form.description" rows="3" auto-resize />
    </div>

    <Message v-if="err('__root__')" severity="error" size="small" variant="simple">
      {{ err("__root__") }}
    </Message>

    <div class="flex justify-end gap-2">
      <Button type="button" label="Cancel" severity="secondary" text @click="emit('cancel')" />
      <Button
        type="submit"
        :label="mode === 'create' ? 'Create program' : 'Save changes'"
        :loading="submitting"
      />
    </div>
  </form>
</template>
