import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/stores/auth";

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("populates me on a successful fetch", async () => {
    const profile = {
      id: "p1",
      display_name: "Ada",
      github_username: "ada",
      is_superadmin: false,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => profile }),
    );

    const auth = useAuthStore();
    await auth.fetchMe();

    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.me?.github_username).toBe("ada");
  });

  it("treats a 401 as anonymous without throwing", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }),
    );

    const auth = useAuthStore();
    await auth.fetchMe();

    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.me).toBeNull();
    expect(auth.loaded).toBe(true);
  });

  it("sends the CSRF header on logout when the cookie is present", async () => {
    document.cookie = "community_csrf=csrf-abc";
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    const auth = useAuthStore();
    auth.me = { id: "p1", display_name: null, github_username: "ada", is_superadmin: false };
    await auth.logout();

    expect(auth.me).toBeNull();
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(init.headers["X-CSRF-Token"]).toBe("csrf-abc");
  });
});
