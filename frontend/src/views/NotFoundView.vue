<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <section class="flex flex-col items-center gap-4 text-center">
    <h1 class="text-2xl font-bold">Page not found</h1>
    <p class="text-surface-600 dark:text-surface-300">
      The page you are looking for does not exist.
    </p>
    <RouterLink to="/" class="text-primary-600 underline"> Return to the home page </RouterLink>
  </section>
</template>
