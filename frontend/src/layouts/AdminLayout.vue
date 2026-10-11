<script setup lang="ts">
// Administrative layout: a left sidebar of admin sections plus the routed admin
// content. The sidebar collapses into a drawer on small screens. Only
// implemented sections are navigable; future sections are shown disabled so the
// information architecture is visible without creating fake routes.
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import { ref } from "vue";
import { RouterLink, RouterView } from "vue-router";

interface AdminSection {
  label: string;
  icon: string;
  to?: string;
  enabled: boolean;
}

// Programs is the only active destination today. Users/Roles/Settings are
// placeholders for future work (no routes, rendered disabled).
const sections: AdminSection[] = [
  { label: "Programs", icon: "pi pi-folder-open", to: "/admin/programs", enabled: true },
  { label: "Users", icon: "pi pi-users", enabled: false },
  { label: "Roles", icon: "pi pi-id-card", enabled: false },
  { label: "Settings", icon: "pi pi-cog", enabled: false },
];

const drawerOpen = ref(false);
</script>

<template>
  <div class="flex flex-1">
    <!-- Desktop sidebar -->
    <aside
      class="hidden w-56 shrink-0 border-r border-surface-200 p-4 md:block dark:border-surface-800"
      aria-label="Administration sections"
    >
      <nav class="flex flex-col gap-1">
        <template v-for="section in sections" :key="section.label">
          <RouterLink
            v-if="section.enabled && section.to"
            :to="section.to"
            class="flex items-center gap-2 rounded px-3 py-2 text-sm hover:bg-surface-100 dark:hover:bg-surface-800"
            active-class="bg-surface-100 font-medium dark:bg-surface-800"
          >
            <i :class="section.icon" aria-hidden="true"></i> {{ section.label }}
          </RouterLink>
          <span
            v-else
            class="flex cursor-not-allowed items-center gap-2 rounded px-3 py-2 text-sm text-surface-400"
            :title="`${section.label} — coming soon`"
            aria-disabled="true"
          >
            <i :class="section.icon" aria-hidden="true"></i> {{ section.label }}
          </span>
        </template>
      </nav>
    </aside>

    <!-- Mobile drawer trigger + content -->
    <div class="flex min-w-0 flex-1 flex-col">
      <div class="border-b border-surface-200 p-2 md:hidden dark:border-surface-800">
        <Button
          icon="pi pi-bars"
          label="Admin menu"
          text
          size="small"
          aria-label="Open administration menu"
          @click="drawerOpen = true"
        />
      </div>
      <div class="min-w-0 flex-1 p-6">
        <RouterView />
      </div>
    </div>

    <Drawer v-model:visible="drawerOpen" header="Administration" position="left">
      <nav class="flex flex-col gap-1">
        <template v-for="section in sections" :key="section.label">
          <RouterLink
            v-if="section.enabled && section.to"
            :to="section.to"
            class="flex items-center gap-2 rounded px-3 py-2 text-sm hover:bg-surface-100 dark:hover:bg-surface-800"
            active-class="bg-surface-100 font-medium dark:bg-surface-800"
            @click="drawerOpen = false"
          >
            <i :class="section.icon" aria-hidden="true"></i> {{ section.label }}
          </RouterLink>
          <span
            v-else
            class="flex cursor-not-allowed items-center gap-2 rounded px-3 py-2 text-sm text-surface-400"
            aria-disabled="true"
          >
            <i :class="section.icon" aria-hidden="true"></i> {{ section.label }}
          </span>
        </template>
      </nav>
    </Drawer>
  </div>
</template>
