<script setup lang="ts">
import Button from "primevue/button";

// Unauthenticated landing/login view. GitHub OAuth is not implemented yet
// (it arrives in a later milestone issue), so the sign-in action is disabled
// and clearly labeled as coming soon rather than appearing broken.
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

    <div class="flex flex-col items-center gap-2">
      <Button
        label="Sign in with GitHub"
        icon="pi pi-github"
        disabled
        aria-describedby="signin-note"
      />
      <p id="signin-note" class="text-sm text-surface-500">GitHub sign-in is coming soon.</p>
    </div>
  </section>
</template>
