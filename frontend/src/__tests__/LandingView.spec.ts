import PrimeVue from "primevue/config";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import LandingView from "@/views/LandingView.vue";

describe("LandingView", () => {
  const factory = () =>
    mount(LandingView, {
      global: {
        plugins: [PrimeVue],
      },
    });

  it("shows the platform welcome heading", () => {
    const wrapper = factory();
    expect(wrapper.get("h1").text()).toContain("omegaUp Community platform");
  });

  it("offers a GitHub sign-in action that is disabled and marked coming soon", () => {
    const wrapper = factory();
    const button = wrapper.get("button");

    // The sign-in affordance is present but intentionally not yet functional.
    expect(button.text()).toContain("Sign in with GitHub");
    expect(button.attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("coming soon");
  });
});
