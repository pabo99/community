import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/stores/auth";

describe("auth store superadmin gating", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("reports isSuperadmin true when /api/me says so", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          id: "p1",
          display_name: "Admin",
          github_username: "pabo99",
          is_superadmin: true,
        }),
      }),
    );

    const auth = useAuthStore();
    await auth.fetchMe();

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.isSuperadmin()).toBe(true);
  });

  it("reports isSuperadmin false for a regular authenticated user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          id: "p2",
          display_name: "User",
          github_username: "octocat",
          is_superadmin: false,
        }),
      }),
    );

    const auth = useAuthStore();
    await auth.fetchMe();

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.isSuperadmin()).toBe(false);
  });

  it("reports isSuperadmin false when anonymous", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }),
    );

    const auth = useAuthStore();
    await auth.fetchMe();

    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.isSuperadmin()).toBe(false);
  });
});
