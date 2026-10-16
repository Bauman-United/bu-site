import { execSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = fileURLToPath(new URL("../..", import.meta.url));

/**
 * Создаёт и сидирует БД `E2E_DB` (по умолчанию bu_e2e); `E2E_EMPTY=1` — только контент клуба.
 * Playwright поднимает webServer раньше globalSetup, поэтому API-сервер вызывает этот файл
 * сам (`node web/e2e/global-setup.ts && uvicorn ...`); как globalSetup он пересидирует БД,
 * когда серверы переиспользуются (`reuseExistingServer`).
 */
export default function globalSetup() {
  const db = process.env.E2E_DB ?? "bu_e2e";
  const empty = process.env.E2E_EMPTY === "1" ? " --empty" : "";
  try { execSync(`createdb ${db}`, { stdio: "ignore" }); } catch { /* уже есть */ }
  execSync(`uv run python -m bu_api.e2e_seed postgresql+psycopg://localhost/${db}${empty}`, {
    cwd: ROOT, stdio: "inherit",
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) globalSetup();
