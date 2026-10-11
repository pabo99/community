<script setup lang="ts">
// Administration landing. Navigation lives in the sidebar (AdminLayout), so
// this screen is a brief orientation rather than a second set of nav cards.
</script>

<template>
  <section class="flex flex-col gap-6">
    <div class="flex flex-col gap-1">
      <h1 class="text-2xl font-bold">Administration</h1>
      <p class="text-surface-600 dark:text-surface-300">
        Manage the platform from the sections in the sidebar. Backend authorization is
        authoritative; these screens are a convenience over the API.
      </p>
    </div>
  </section>
</template>
