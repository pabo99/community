<script setup lang="ts">
// Minimal application shell: a header with the global workspace navigation, a
// main content region, and a footer. Layout and spacing are owned by Tailwind
// utilities; complex components are provided by PrimeVue (see views).
//
// The global navigation lists top-level workspaces, not individual admin
// sections. Programs lives inside the Administration workspace sidebar
// (AdminLayout), not in this global bar.
import Toast from "primevue/toast";
import { computed } from "vue";
import { RouterLink } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface Workspace {
  label: string;
  to: string;
  // Shown only when the predicate is true. Workspaces without a predicate are
  // always visible. Visibility is UX only; the backend enforces access.
  visible: boolean;
}

// Workspaces reflect real, implemented destinations. Contributor and Mentor
// surfaces do not exist yet, so we do not advertise fake modules — only
// Administration is listed, and only to superadmins.
const workspaces = computed<Workspace[]>(() => [
  { label: "Administration", to: "/admin", visible: auth.isSuperadmin() },
]);
</script>

<template>
  <div
    class="flex min-h-screen flex-col bg-surface-50 text-surface-900 dark:bg-surface-950 dark:text-surface-0"
  >
    <Toast />
    <header class="border-b border-surface-200 dark:border-surface-800">
      <div class="mx-auto flex w-full max-w-screen-2xl items-center gap-6 px-6 py-4 lg:px-8">
        <RouterLink to="/" class="text-lg font-semibold">omegaUp Community</RouterLink>
        <nav class="flex items-center gap-4 text-sm" aria-label="Workspaces">
          <template v-for="workspace in workspaces" :key="workspace.to">
            <RouterLink
              v-if="workspace.visible"
              :to="workspace.to"
              class="text-primary-600 hover:underline"
            >
              {{ workspace.label }}
            </RouterLink>
          </template>
        </nav>
      </div>
    </header>

    <main class="mx-auto flex w-full max-w-screen-2xl flex-1 flex-col px-6 py-10 lg:px-8">
      <slot />
    </main>

    <footer class="border-t border-surface-200 dark:border-surface-800">
      <div class="mx-auto w-full max-w-screen-2xl px-6 py-4 text-sm text-surface-500 lg:px-8">
        Contributor Community Platform
      </div>
    </footer>
  </div>
</template>
