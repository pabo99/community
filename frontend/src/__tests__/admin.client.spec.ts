import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createEdition, createProgram, updateEdition } from "@/api/admin";
import { ApiError, errorDetail, parseValidationErrors } from "@/api/client";

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
    json: async () => body,
  } as unknown as Response;
}

describe("admin API client", () => {
  beforeEach(() => {
    document.cookie = "community_csrf=csrf-token-xyz";
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("POST program sends name/icon, credentials, and CSRF header", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(201, {
        id: "p1",
        slug: "gsoc",
        name: "GSoC",
        description: null,
        icon: "github",
        is_standard: false,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const created = await createProgram({ name: "GSoC", icon: "github" });
    expect(created.slug).toBe("gsoc");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/programs");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(init.headers["X-CSRF-Token"]).toBe("csrf-token-xyz");
    expect(JSON.parse(init.body)).toEqual({ name: "GSoC", icon: "github" });
  });

  it("POST edition sends year/period (never source/status)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { id: "e1" }));
    vi.stubGlobal("fetch", fetchMock);

    await createEdition("p1", { year: 2026, period: "second_semester" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/admin/programs/p1/editions");
    const body = JSON.parse(init.body);
    expect(body).toMatchObject({ year: 2026, period: "second_semester" });
    expect(body).not.toHaveProperty("source");
    expect(body).not.toHaveProperty("status");
  });

  it("PATCH edition sends only provided mutable fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { id: "e1" }));
    vi.stubGlobal("fetch", fetchMock);

    await updateEdition("e1", { ends_on: "2026-11-30" });
    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ ends_on: "2026-11-30" });
  });

  it("throws ApiError carrying the parsed body on non-2xx", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(409, { detail: "slug exists" })));
    await expect(createProgram({ name: "GSoC", icon: "github" })).rejects.toMatchObject({
      status: 409,
    });
  });

  it("parseValidationErrors maps FastAPI 422 detail to field messages", () => {
    const body = {
      detail: [
        { loc: ["body", "icon"], msg: "Input should be ...", type: "literal_error" },
        { loc: ["body"], msg: "ends_on must be on or after starts_on", type: "value_error" },
      ],
    };
    const errors = parseValidationErrors(body);
    expect(errors.icon).toContain("Input should be");
    expect(errors.__root__).toContain("ends_on");
  });

  it("errorDetail extracts a string detail with a fallback", () => {
    expect(errorDetail({ detail: "boom" }, "fallback")).toBe("boom");
    expect(errorDetail(null, "fallback")).toBe("fallback");
  });

  it("ApiError defaults body to null (backward compatible)", () => {
    const err = new ApiError(401, "x");
    expect(err.status).toBe(401);
    expect(err.body).toBeNull();
  });
});
