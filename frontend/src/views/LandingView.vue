<script setup lang="ts">
import Button from "primevue/button";
import { onMounted } from "vue";

import { useAuthStore } from "@/stores/auth";

// Unauthenticated landing/login view. Signing in starts the GitHub OAuth flow
// against the same-origin backend; the backend owns the session cookie.
const auth = useAuthStore();

onMounted(() => {
  // Resolve current session (no-op/anonymous if not signed in).
  void auth.fetchMe();
});
</script>

<template>
  <section class="flex flex-col items-center gap-6 text-center">
    <div class="flex flex-col gap-3">
      <h1 class="text-3xl font-bold tracking-tight sm:text-4xl">
        Welcome to the omegaUp Community platform
      </h1>
      <p class="max-w-2xl text-base text-surface-600 dark:text-surface-300">
        A home for omegaUp contributors across programs such as GSoC, internships, residencies, and
        volunteer initiatives.
      </p>
    </div>

    <div v-if="auth.isAuthenticated()" class="flex flex-col items-center gap-3">
      <p class="text-base">
        Signed in as
        <span class="font-semibold">{{ auth.me?.github_username ?? auth.me?.display_name }}</span>
      </p>
      <Button label="Sign out" icon="pi pi-sign-out" severity="secondary" @click="auth.logout()" />
    </div>

    <div v-else class="flex flex-col items-center gap-2">
      <Button label="Sign in with GitHub" icon="pi pi-github" @click="auth.login()" />
    </div>
  </section>
</template>
