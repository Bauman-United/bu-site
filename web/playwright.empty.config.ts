import { defineConfig, devices } from "@playwright/test";

// Пустая база: отдельные порты и БД, чтобы не пересекаться с основным прогоном.
const API = "http://localhost:8002";
const WEB = "http://localhost:3200";
const DB = "bu_e2e_empty";

// Читает e2e/global-setup.ts (globalSetup и команда API-сервера).
process.env.E2E_DB = DB;
process.env.E2E_EMPTY = "1";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "empty.spec.ts",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: WEB },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
  webServer: [
    {
      command: "node web/e2e/global-setup.ts && uv run uvicorn bu_api.app:build --factory --port 8002",
      cwd: "..",
      url: `${API}/health`,
      env: { BU_DATABASE_URL: `postgresql+psycopg://localhost/${DB}`, E2E_DB: DB, E2E_EMPTY: "1" },
      reuseExistingServer: !process.env.CI,
    },
    {
      // Сборка с BU_NOINDEX=0, запуск с BU_NOINDEX=1: empty.spec проверяет, что robots.txt берёт рантайм.
      command: "pnpm build && pnpm check:robots && BU_NOINDEX=1 pnpm start --port 3200",
      url: WEB,
      timeout: 240_000,
      env: {
        BU_API_URL: API, BU_SITE_URL: "https://baumanunited.test", BU_NOINDEX: "0",
        BU_REVALIDATE_SECRET: "e2e",
      },
      reuseExistingServer: !process.env.CI,
    },
  ],
});
