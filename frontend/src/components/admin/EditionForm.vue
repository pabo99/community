<script setup lang="ts">
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, reactive, ref, watch } from "vue";

import type { Edition, EditionCreate, EditionPeriod, EditionUpdate } from "@/api/admin";
import { EDITION_PERIODS } from "@/api/admin";

const props = defineProps<{
  mode: "create" | "edit";
  edition?: Edition;
  submitting?: boolean;
  fieldErrors?: Record<string, string>;
}>();

const emit = defineEmits<{
  (e: "submit-create", payload: EditionCreate): void;
  (e: "submit-update", payload: EditionUpdate): void;
  // `dirty` tells the parent whether the form has unsaved changes, so it can
  // decide whether to confirm before discarding (edit mode) or just close.
  (e: "cancel", dirty: boolean): void;
}>();

function toDate(iso: string | null | undefined): Date | null {
  return iso ? new Date(`${iso}T00:00:00`) : null;
}
function toIso(d: Date | null): string | null {
  if (!d) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const currentYear = new Date().getUTCFullYear();

// Year choices: the current year plus/minus five (eleven options), defaulting
// to the current year. The year is the edition's identity, not a cap on its
// operational dates — a 2027 edition may legitimately start in 2026.
const yearOptions = Array.from({ length: 11 }, (_, i) => currentYear - 5 + i).map((y) => ({
  label: String(y),
  value: y,
}));

// Default (starts_on, ends_on) for a year/period, mirroring the backend:
//   annual          -> Jan 1  .. Dec 31
//   first semester  -> Jan 1  .. Jun 30
//   second semester -> Jul 1  .. Dec 31
function suggestedDates(year: number, period: EditionPeriod): { start: Date; end: Date } {
  if (period === "first_semester") {
    return { start: new Date(year, 0, 1), end: new Date(year, 5, 30) };
  }
  if (period === "second_semester") {
    return { start: new Date(year, 6, 1), end: new Date(year, 11, 31) };
  }
  return { start: new Date(year, 0, 1), end: new Date(year, 11, 31) };
}

const initialSuggestion = suggestedDates(currentYear, "annual");

const form = reactive({
  year: props.edition ? Number(props.edition.slug.slice(0, 4)) : currentYear,
  period: (props.edition?.period ?? "annual") as EditionPeriod,
  name: props.edition?.name ?? "",
  startsOn: props.edition ? toDate(props.edition.starts_on) : initialSuggestion.start,
  endsOn: props.edition ? toDate(props.edition.ends_on) : initialSuggestion.end,
});

// Track whether the user has hand-edited each date. Once edited, year/period
// changes stop overwriting that field so customized dates are preserved.
const startEdited = ref(false);
const endEdited = ref(false);

// In create mode, refresh untouched date fields whenever year or period change.
if (props.mode === "create") {
  watch(
    () => [form.year, form.period] as const,
    ([year, period]) => {
      const { start, end } = suggestedDates(year, period);
      if (!startEdited.value) form.startsOn = start;
      if (!endEdited.value) form.endsOn = end;
    },
  );
}

const localErrors = ref<Record<string, string>>({});
function err(field: string): string | undefined {
  return localErrors.value[field] ?? props.fieldErrors?.[field];
}

// Preview of the slug that will be generated (create mode only).
const slugPreview = computed(() => {
  if (form.period === "annual") return `${form.year}`;
  return `${form.year}-${form.period === "first_semester" ? "1" : "2"}`;
});

// Whether the form differs from its initial values. In edit mode this compares
// the mutable fields (name, dates) against the loaded edition; in create mode
// it compares against the create defaults. The parent uses it to decide whether
// a Cancel needs a discard confirmation.
const dirty = computed(() => {
  if (props.mode === "edit") {
    const nameChanged = form.name.trim() !== (props.edition?.name ?? "");
    const startChanged = toIso(form.startsOn) !== (props.edition?.starts_on ?? null);
    const endChanged = toIso(form.endsOn) !== (props.edition?.ends_on ?? null);
    return nameChanged || startChanged || endChanged;
  }
  // Create mode: dirty once the user typed a name or hand-edited a date.
  return form.name.trim() !== "" || startEdited.value || endEdited.value;
});

function cancel(): void {
  emit("cancel", dirty.value);
}

function validateDates(): boolean {
  localErrors.value = {};
  if (form.startsOn && form.endsOn && form.endsOn < form.startsOn) {
    localErrors.value.ends_on = "End date must be on or after the start date.";
    return false;
  }
  return true;
}

function submit(): void {
  if (!validateDates()) return;

  if (props.mode === "create") {
    const payload: EditionCreate = {
      year: form.year,
      period: form.period,
      name: form.name.trim() ? form.name.trim() : null,
      starts_on: toIso(form.startsOn),
      ends_on: toIso(form.endsOn),
    };
    emit("submit-create", payload);
    return;
  }

  // Edit: only name/dates are mutable; send only changed fields. Dates remain
  // required, so we never send null (the DatePicker clear is disabled in edit).
  const payload: EditionUpdate = {};
  if (form.name.trim() !== (props.edition?.name ?? "")) {
    payload.name = form.name.trim();
  }
  const startsIso = toIso(form.startsOn);
  if (startsIso && startsIso !== props.edition?.starts_on) {
    payload.starts_on = startsIso;
  }
  const endsIso = toIso(form.endsOn);
  if (endsIso && endsIso !== props.edition?.ends_on) {
    payload.ends_on = endsIso;
  }
  emit("submit-update", payload);
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="submit">
    <template v-if="mode === 'create'">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div class="flex flex-col gap-1">
          <label for="edition-year" class="text-sm font-medium">Year</label>
          <Select
            id="edition-year"
            v-model="form.year"
            :options="yearOptions"
            option-label="label"
            option-value="value"
          />
        </div>
        <div class="flex flex-col gap-1">
          <label for="edition-period" class="text-sm font-medium">Period</label>
          <Select
            id="edition-period"
            v-model="form.period"
            :options="EDITION_PERIODS"
            option-label="label"
            option-value="value"
          />
        </div>
      </div>
      <small class="text-surface-500">
        Identifier will be <span class="font-mono">{{ slugPreview }}</span
        >. The year is the edition's identity; the dates below are suggested from the year and
        period and can be adjusted freely.
      </small>
    </template>

    <div class="flex flex-col gap-1">
      <label for="edition-name" class="text-sm font-medium">Name</label>
      <InputText
        id="edition-name"
        v-model="form.name"
        :placeholder="mode === 'create' ? 'Auto-generated if left blank' : ''"
        :invalid="!!err('name')"
      />
      <Message v-if="err('name')" severity="error" size="small" variant="simple">
        {{ err("name") }}
      </Message>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div class="flex flex-col gap-1">
        <label for="edition-starts" class="text-sm font-medium">Start date</label>
        <DatePicker
          id="edition-starts"
          v-model="form.startsOn"
          date-format="yy-mm-dd"
          show-icon
          :manual-input="false"
          @update:model-value="startEdited = true"
        />
      </div>
      <div class="flex flex-col gap-1">
        <label for="edition-ends" class="text-sm font-medium">End date</label>
        <DatePicker
          id="edition-ends"
          v-model="form.endsOn"
          date-format="yy-mm-dd"
          show-icon
          :manual-input="false"
          :invalid="!!err('ends_on')"
          @update:model-value="endEdited = true"
        />
        <Message v-if="err('ends_on')" severity="error" size="small" variant="simple">
          {{ err("ends_on") }}
        </Message>
      </div>
    </div>

    <Message v-if="err('__root__')" severity="error" size="small" variant="simple">
      {{ err("__root__") }}
    </Message>

    <div class="flex justify-end gap-2">
      <Button type="button" label="Cancel" severity="secondary" text @click="cancel" />
      <Button
        type="submit"
        :label="mode === 'create' ? 'Create edition' : 'Save changes'"
        :loading="submitting"
      />
    </div>
  </form>
</template>
