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
});
