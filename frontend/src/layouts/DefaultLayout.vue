<script setup lang="ts">
// Minimal application shell: a header, a main content region, and a footer.
// Layout and spacing are owned by Tailwind utilities; complex components are
// provided by PrimeVue (see views).
import { RouterLink } from "vue-router";

import { useAuthStore } from "@/stores/auth";

// The admin link is shown to superadmins only (UX). The route itself is
// guarded and the backend enforces authorization regardless.
const auth = useAuthStore();
</script>

<template>
  <div
    class="flex min-h-screen flex-col bg-surface-50 text-surface-900 dark:bg-surface-950 dark:text-surface-0"
  >
    <header class="border-b border-surface-200 dark:border-surface-800">
      <div class="mx-auto flex w-full max-w-5xl items-center gap-6 px-6 py-4">
        <RouterLink to="/" class="text-lg font-semibold">omegaUp Community</RouterLink>
        <nav v-if="auth.isSuperadmin()" class="flex items-center gap-4 text-sm">
          <RouterLink to="/admin" class="text-primary-600 hover:underline">Admin</RouterLink>
        </nav>
      </div>
    </header>

    <main class="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
      <slot />
    </main>

    <footer class="border-t border-surface-200 dark:border-surface-800">
      <div class="mx-auto w-full max-w-5xl px-6 py-4 text-sm text-surface-500">
        Contributor Community Platform
      </div>
    </footer>
  </div>
</template>
