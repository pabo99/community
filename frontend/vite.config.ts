import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    // Listen on all interfaces so the dev server is reachable from the host
    // when running inside the Docker Compose `frontend` container.
    host: true,
    port: 5173,
    // Native file watching is used by default; HMR works through the bind
    // mount. If a host filesystem does not deliver change events into the
    // container, set CHOKIDAR_USEPOLLING=true to enable polling as a fallback.
    watch: {
      usePolling: process.env.CHOKIDAR_USEPOLLING === "true",
    },
  },
});
