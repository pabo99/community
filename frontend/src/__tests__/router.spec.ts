import { describe, expect, it } from "vitest";

import router from "@/router";

describe("router", () => {
  it("resolves the root path to the landing route", () => {
    const resolved = router.resolve("/");
    expect(resolved.name).toBe("landing");
  });

  it("resolves an unknown path to the not-found route", () => {
    const resolved = router.resolve("/does/not/exist");
    expect(resolved.name).toBe("not-found");
  });

  it("guards the admin program/edition routes with requiresSuperadmin", () => {
    for (const path of [
      "/admin",
      "/admin/programs",
      "/admin/programs/abc",
      "/admin/editions/abc",
    ]) {
      const resolved = router.resolve(path);
      expect(resolved.meta.requiresSuperadmin).toBe(true);
    }
  });
});
