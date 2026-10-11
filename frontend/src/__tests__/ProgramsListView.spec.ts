import { flushPromises, mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import ToastService from "primevue/toastservice";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ProgramsListView from "@/views/admin/ProgramsListView.vue";

const push = vi.fn();
vi.mock("vue-router", () => ({
  useRouter: () => ({ push }),
  RouterLink: { template: "<a><slot /></a>" },
}));

function jsonResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => "application/json" },
    json: async () => body,
  } as unknown as Response;
}

function mountView() {
  return mount(ProgramsListView, { global: { plugins: [PrimeVue, ToastService] } });
}

const PROGRAM = {
  id: "p1",
  slug: "gsoc",
  name: "Google Summer of Code",
  description: null,
  icon: "github",
  is_standard: true,
  created_at: "",
  updated_at: "",
  edition_count: 2,
  active_editions: [{ id: "e1", slug: "2026", name: "GSoC 2026" }],
};

describe("ProgramsListView", () => {
  beforeEach(() => {
    document.cookie = "community_csrf=csrf";
    push.mockReset();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders an empty state when there are no programs", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [])));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("No programs yet.");
  });

  it("lists programs with edition count and active editions", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [PROGRAM])));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("Google Summer of Code");
    expect(wrapper.text()).toContain("2026"); // active edition slug chip
    expect(wrapper.text()).toContain("Manage");
  });

  it("shows a load-error state", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(500, { detail: "boom" })));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("Could not load programs.");
  });

  it("disables delete for a program that still has editions", async () => {
    // PROGRAM has edition_count: 2 — deletion is empty-only, so the row's
    // delete action must be disabled rather than offering a flow that 409s.
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [PROGRAM])));
    const wrapper = mountView();
    await flushPromises();

    const deleteBtn = wrapper.get(
      `button[aria-label="Cannot delete ${PROGRAM.name}: remove its editions first"]`,
    );
    expect((deleteBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it("enables delete for an empty program", async () => {
    const empty = { ...PROGRAM, id: "p2", name: "Empty", edition_count: 0, active_editions: [] };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [empty])));
    const wrapper = mountView();
    await flushPromises();

    const deleteBtn = wrapper.get(`button[aria-label="Delete ${empty.name}"]`);
    expect((deleteBtn.element as HTMLButtonElement).disabled).toBe(false);
  });
});
