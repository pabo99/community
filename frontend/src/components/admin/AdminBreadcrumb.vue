<script setup lang="ts">
// Breadcrumb trail for the administration screens.
//
// The trail reads `Administration / Programs / <program name> / <edition slug>`
// with each ancestor a working link. Callers pass only the labels they can
// resolve (a program name once the program loads, an edition slug once the
// edition loads); the fixed `Administration` / `Programs` prefix is always
// present. Human-readable names are shown, never UUIDs. There is no separate
// "Edit edition" level — editing happens in place on the edition screen.
import Breadcrumb from "primevue/breadcrumb";
import { computed } from "vue";
import { useRouter } from "vue-router";

import type { MenuItem } from "primevue/menuitem";

const props = defineProps<{
  // Program crumb. Provide `name` for the label and `id` to link to its detail.
  program?: { id: string; name: string };
  // Edition crumb (leaf). Shown as the edition slug; rendered as plain text
  // because it is the current page.
  editionSlug?: string;
}>();

const router = useRouter();

const home = computed<MenuItem>(() => ({
  label: "Administration",
  command: () => router.push({ name: "admin" }),
}));

const items = computed<MenuItem[]>(() => {
  const trail: MenuItem[] = [
    { label: "Programs", command: () => router.push({ name: "admin-programs" }) },
  ];
  if (props.program) {
    const program = props.program;
    trail.push({
      label: program.name,
      command: () =>
        router.push({ name: "admin-program-detail", params: { programId: program.id } }),
    });
  }
  if (props.editionSlug) {
    // Leaf: no command, so PrimeVue renders it as the current (non-link) crumb.
    trail.push({ label: props.editionSlug });
  }
  return trail;
});
</script>

<template>
  <Breadcrumb :home="home" :model="items" class="!bg-transparent !p-0 text-sm" />
</template>
