import { emptyValues, fieldErrors, stateFromResponse, valuesFromForm } from "./join";

function form(entries: Record<string, string>): FormData {
  const fd = new FormData();
  for (const [k, v] of Object.entries(entries)) fd.set(k, v);
  return fd;
}

describe("valuesFromForm", () => {
  it("reads and trims all fields, missing ones become empty", () => {
    const v = valuesFromForm(form({ name: "  Иван ", age: " 21 ", position: "Вратарь" }));
    expect(v).toEqual({ ...emptyValues, name: "Иван", age: "21", position: "Вратарь" });
  });
});

describe("fieldErrors", () => {
  it("maps FastAPI 422 detail to Russian per-field messages", () => {
    const detail = [
      { loc: ["body", "experience"], msg: "too short", type: "string_too_short" },
      { loc: ["body", "age"], msg: "bad", type: "greater_than_equal" },
      { loc: ["body", "website"], msg: "x", type: "x" },
      { loc: ["body"], msg: "x", type: "x" },
    ];
    const errors = fieldErrors(detail);
    expect(errors.experience).toMatch(/от 10 до 1500/);
    expect(errors.age).toMatch(/14.*70/);
    expect(Object.keys(errors).sort()).toEqual(["age", "experience"]);
  });
  it("tolerates garbage", () => {
    expect(fieldErrors(undefined)).toEqual({});
    expect(fieldErrors("nope")).toEqual({});
  });
});

describe("stateFromResponse", () => {
  const values = { ...emptyValues, name: "Иван" };
  it("success", () => {
    expect(stateFromResponse(200, { ok: true }, values).status).toBe("success");
  });
  it("422 → invalid with field errors and preserved values", () => {
    const s = stateFromResponse(422, { detail: [{ loc: ["body", "name"], msg: "x" }] }, values);
    expect(s.status).toBe("invalid");
    expect(s.errors.name).toBeTruthy();
    expect(s.values).toEqual(values);
  });
  it("429 → rate-limited message", () => {
    const s = stateFromResponse(429, {}, values);
    expect(s.status).toBe("error");
    expect(s.message).toMatch(/Слишком много/);
  });
  it.each([502, 503, 500])("%i → generic error", (status) => {
    const s = stateFromResponse(status, {}, values);
    expect(s.status).toBe("error");
    expect(s.message).toMatch(/Не получилось/);
  });
});
