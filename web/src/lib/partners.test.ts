import { emptyPartnerValues, partnerFieldErrors, partnerStateFromResponse, partnerValuesFromForm } from "./partners";

function form(entries: Record<string, string>): FormData {
  const fd = new FormData();
  for (const [k, v] of Object.entries(entries)) fd.set(k, v);
  return fd;
}

describe("partnerValuesFromForm", () => {
  it("reads and trims fields, missing ones become empty", () => {
    const v = partnerValuesFromForm(form({ about: "  Магазин экипировки ", name: "лишнее" }));
    expect(v).toEqual({ ...emptyPartnerValues, about: "Магазин экипировки" });
  });
});

describe("partnerFieldErrors", () => {
  it("maps FastAPI 422 detail to per-field messages", () => {
    const errors = partnerFieldErrors([
      { loc: ["body", "about"], msg: "too short" },
      { loc: ["body", "contact"], msg: "too short" },
      { loc: ["body", "website"], msg: "x" },
    ]);
    expect(errors.about).toMatch(/от 10 до 2000/);
    expect(errors.contact).toMatch(/от 3 до 200/);
    expect(Object.keys(errors).sort()).toEqual(["about", "contact"]);
  });
});

describe("partnerStateFromResponse", () => {
  const values = { ...emptyPartnerValues, about: "Предложение о форме" };
  it("success resets values", () => {
    const s = partnerStateFromResponse(200, { ok: true }, values);
    expect(s.status).toBe("success");
    expect(s.values).toEqual(emptyPartnerValues);
  });
  it("422 → invalid with preserved values", () => {
    const s = partnerStateFromResponse(422, { detail: [{ loc: ["body", "contact"] }] }, values);
    expect(s.status).toBe("invalid");
    expect(s.errors.contact).toBeTruthy();
    expect(s.values).toEqual(values);
  });
  it("429 → rate-limited message", () => {
    expect(partnerStateFromResponse(429, {}, values).message).toMatch(/Слишком много/);
  });
  it.each([500, 502, 503])("%i → generic error", (status) => {
    const s = partnerStateFromResponse(status, {}, values);
    expect(s.status).toBe("error");
    expect(s.message).toMatch(/Не получилось/);
  });
});
