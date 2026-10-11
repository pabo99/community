<script setup lang="ts">
import Tag from "primevue/tag";
import { computed } from "vue";

import type { EditionSource } from "@/api/admin";

const props = defineProps<{ source: EditionSource; externalId?: string | null }>();

// Read-only provenance. Manually created editions are always "Community";
// "omegaUp" originates only from a future trusted integration and does NOT
// imply any synchronization has occurred yet.
const label = computed(() => (props.source === "omegaup" ? "omegaUp" : "Community"));
const severity = computed(() => (props.source === "omegaup" ? "info" : "secondary"));
</script>

<template>
  <span class="inline-flex items-center gap-2">
    <Tag :value="label" :severity="severity" :aria-label="`Source: ${label}`" />
    <span
      v-if="source === 'omegaup' && externalId"
      class="text-xs text-surface-500"
      :title="`External reference: ${externalId}`"
    >
      ref: {{ externalId }}
    </span>
  </span>
</template>
