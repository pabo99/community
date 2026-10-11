<script setup lang="ts">
import Tag from "primevue/tag";
import { computed } from "vue";

import type { EditionStatus } from "@/api/admin";

const props = defineProps<{ status: EditionStatus }>();

const SEVERITY: Record<EditionStatus, string> = {
  upcoming: "info",
  active: "success",
  finished: "secondary",
};

const LABEL: Record<EditionStatus, string> = {
  upcoming: "Upcoming",
  active: "Active",
  finished: "Finished",
};

const severity = computed(() => SEVERITY[props.status]);
const label = computed(() => LABEL[props.status]);
</script>

<template>
  <Tag :value="label" :severity="severity" :aria-label="`Status: ${label}`" />
</template>
