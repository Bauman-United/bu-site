import { execSync } from "node:child_process";

export default function globalSetup() {
  try { execSync("createdb bu_e2e", { stdio: "ignore" }); } catch { /* уже есть */ }
  execSync("uv run python -m bu_api.e2e_seed postgresql+psycopg://localhost/bu_e2e", {
    cwd: "..", stdio: "inherit",
  });
}
