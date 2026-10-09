<script setup lang="ts">
import Button from "primevue/button";
import { onMounted, ref } from "vue";

import { apiGet, ApiError } from "@/api/client";

// Minimal admin landing for M1-07. It verifies superadmin access end-to-end by
// calling the protected /api/admin/ping endpoint. The mentor-request inbox is a
// follow-on feature (M1-07b).
const status = ref<"idle" | "ok" | "forbidden" | "error">("idle");

async function checkAccess(): Promise<void> {
  status.value = "idle";
  try {
    await apiGet<{ status: string }>("/api/admin/ping");
    status.value = "ok";
  } catch (error) {
    status.value = error instanceof ApiError && error.status === 403 ? "forbidden" : "error";
  }
}

onMounted(checkAccess);
</script>

<template>
  <section class="flex flex-col gap-4">
    <h1 class="text-2xl font-bold">Administration</h1>
    <p class="text-surface-600 dark:text-surface-300">
      Platform administration. Backend authorization is authoritative.
    </p>

    <p v-if="status === 'ok'" class="text-green-600">Superadmin access confirmed.</p>
    <p v-else-if="status === 'forbidden'" class="text-red-600">
      You do not have administrator access.
    </p>
    <p v-else-if="status === 'error'" class="text-red-600">
      Could not verify administrator access.
    </p>

    <div>
      <Button
        label="Re-check access"
        icon="pi pi-refresh"
        severity="secondary"
        @click="checkAccess"
      />
    </div>
  </section>
</template>
