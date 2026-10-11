import { fileURLToPath } from "node:url";

import { mergeConfig } from "vite";
import { configDefaults, defineConfig } from "vitest/config";

import viteConfig from "./vite.config.ts";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/__tests__/setup.ts"],
      exclude: [...configDefaults.exclude, "e2e/**", "src/__tests__/setup.ts"],
      root: fileURLToPath(new URL("./", import.meta.url)),
    },
  }),
);
