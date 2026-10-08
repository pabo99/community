<script setup lang="ts">
// Minimal application shell: a header, a main content region, and a footer.
// Layout and spacing are owned by Tailwind utilities; complex components are
// provided by PrimeVue (see views).
</script>

<template>
  <div
    class="flex min-h-screen flex-col bg-surface-50 text-surface-900 dark:bg-surface-950 dark:text-surface-0"
  >
    <header class="border-b border-surface-200 dark:border-surface-800">
      <div class="mx-auto flex w-full max-w-5xl items-center px-6 py-4">
        <span class="text-lg font-semibold">omegaUp Community</span>
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
