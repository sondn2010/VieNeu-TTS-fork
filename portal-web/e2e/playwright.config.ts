import { defineConfig } from "@playwright/test";

/**
 * Runs against the real compose stack (`make portal-up` + a CPU engine) —
 * never against a mocked API, since the point of this suite is proving the
 * Next.js static export genuinely talks to the FastAPI portal end to end.
 * `PORTAL_BASE_URL` defaults to the port `docker-compose.portal.yml` binds.
 */
export default defineConfig({
  testDir: ".",
  testMatch: "**/*.spec.ts",
  timeout: 60_000,
  fullyParallel: false,
  retries: 0,
  use: {
    baseURL: process.env.PORTAL_BASE_URL ?? "http://localhost:8100",
    trace: "retain-on-failure",
  },
});
