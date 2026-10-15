import { defineConfig, devices } from "@playwright/test";

const API = "http://localhost:8001";
const WEB = "http://localhost:3100";

export default defineConfig({
  testDir: "./e2e",
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
      command: "uv run uvicorn bu_api.app:build --factory --port 8001",
      cwd: "..",
      url: `${API}/health`,
      env: { BU_DATABASE_URL: "postgresql+psycopg://localhost/bu_e2e" },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "pnpm build && pnpm start --port 3100",
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
