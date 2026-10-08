import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import PrimeVue from "primevue/config";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import LandingView from "@/views/LandingView.vue";

describe("LandingView", () => {
  beforeEach(() => {
    // onMounted calls fetchMe(); return anonymous (401) by default.
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({}) }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  const factory = () =>
    mount(LandingView, {
      global: {
        plugins: [createPinia(), PrimeVue],
      },
    });

  it("shows the platform welcome heading", () => {
    const wrapper = factory();
    expect(wrapper.get("h1").text()).toContain("omegaUp Community platform");
  });

  it("offers an actionable GitHub sign-in affordance when anonymous", () => {
    const wrapper = factory();
    const button = wrapper.get("button");

    expect(button.text()).toContain("Sign in with GitHub");
    // The sign-in button is now functional (not disabled).
    expect(button.attributes("disabled")).toBeUndefined();
  });

  it("initiates GitHub OAuth when the sign-in button is clicked", async () => {
    const assign = vi.fn();
    vi.stubGlobal("location", { assign } as unknown as Location);

    const wrapper = factory();
    await wrapper.get("button").trigger("click");

    expect(assign).toHaveBeenCalledWith("/api/auth/github/login");
  });
});
