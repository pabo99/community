import { mount } from "@vue/test-utils";
import PrimeVue from "primevue/config";
import { describe, expect, it } from "vitest";

import type { Edition } from "@/api/admin";
import EditionForm from "@/components/admin/EditionForm.vue";

type FormProps = InstanceType<typeof EditionForm>["$props"];

function mountForm(props: FormProps) {
  return mount(EditionForm, { props, global: { plugins: [PrimeVue] } });
}

const EDITION: Edition = {
  id: "e1",
  program_id: "p1",
  slug: "2026",
  name: "GSoC 2026",
  period: "annual",
  status: "active",
  starts_on: "2026-01-01",
  ends_on: "2026-12-31",
  source: "community",
  external_id: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("EditionForm (create mode)", () => {
  it("emits a year+period create payload (no source/status/slug)", async () => {
    const wrapper = mountForm({ mode: "create" });
    await wrapper.get("form").trigger("submit");

    const payload = wrapper.emitted("submit-create")![0][0] as Record<string, unknown>;
    expect(payload).toHaveProperty("year");
    expect(payload.period).toBe("annual");
    expect(payload).not.toHaveProperty("source");
    expect(payload).not.toHaveProperty("status");
    expect(payload).not.toHaveProperty("slug");
  });

  it("defaults the year to the current year and prepopulates annual dates", async () => {
    const wrapper = mountForm({ mode: "create" });
    await wrapper.get("form").trigger("submit");

    const payload = wrapper.emitted("submit-create")![0][0] as Record<string, unknown>;
    const thisYear = new Date().getUTCFullYear();
    expect(payload.year).toBe(thisYear);
    // Annual default spans the whole calendar year.
    expect(payload.starts_on).toBe(`${thisYear}-01-01`);
    expect(payload.ends_on).toBe(`${thisYear}-12-31`);
  });
});

describe("EditionForm (edit mode)", () => {
  it("emits only changed mutable fields", async () => {
    const wrapper = mountForm({ mode: "edit", edition: EDITION });
    await wrapper.get("#edition-name").setValue("GSoC 2026 (renamed)");
    await wrapper.get("form").trigger("submit");

    const payload = wrapper.emitted("submit-update")![0][0] as Record<string, unknown>;
    expect(payload).toEqual({ name: "GSoC 2026 (renamed)" });
    expect(payload).not.toHaveProperty("slug");
    expect(payload).not.toHaveProperty("source");
    expect(payload).not.toHaveProperty("status");
  });

  it("does not show year/period selectors in edit mode", () => {
    const wrapper = mountForm({ mode: "edit", edition: EDITION });
    expect(wrapper.find("#edition-year").exists()).toBe(false);
    expect(wrapper.find("#edition-period").exists()).toBe(false);
  });

  it("surfaces an injected date-range field error", async () => {
    const wrapper = mountForm({
      mode: "edit",
      edition: EDITION,
      fieldErrors: { ends_on: "End date must be on or after the start date." },
    });
    expect(wrapper.text()).toContain("End date must be on or after the start date.");
  });

  function cancelButton(wrapper: ReturnType<typeof mountForm>) {
    // The Cancel button is the one labelled "Cancel" (DatePicker also renders
    // type="button" trigger buttons, so select by label text, not type).
    return wrapper.findAll("button").find((b) => b.text().trim() === "Cancel")!;
  }

  it("emits cancel with dirty=false when nothing changed", async () => {
    const wrapper = mountForm({ mode: "edit", edition: EDITION });
    await cancelButton(wrapper).trigger("click");

    const payload = wrapper.emitted("cancel")![0];
    expect(payload[0]).toBe(false);
  });

  it("emits cancel with dirty=true after an unsaved edit", async () => {
    const wrapper = mountForm({ mode: "edit", edition: EDITION });
    await wrapper.get("#edition-name").setValue("GSoC 2026 (renamed)");
    await cancelButton(wrapper).trigger("click");

    const payload = wrapper.emitted("cancel")![0];
    expect(payload[0]).toBe(true);
  });
});
