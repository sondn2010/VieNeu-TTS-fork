import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api/api-error";
import { I18nProvider } from "../../lib/i18n/i18n-provider";
import { ThemeProvider } from "../../lib/theme/theme-provider";
import AdminLayout from "./layout";

const apiFetchMock = vi.fn();
const replaceMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock, push: vi.fn() }),
  usePathname: () => "/admin/users/",
}));

const ADMIN_PROFILE = {
  id: "a1",
  email: "admin@example.com",
  username: "admin",
  avatar_initials: "AD",
  plan_tier: "PRO",
  token_balance: 1000,
  token_quota_total: 2000,
  daily_char_limit: 50000,
  daily_char_remaining: 50000,
  plan_expires_at: null,
  has_accepted_tts_terms: true,
  terms_version: "v1",
  onboarding_completed_steps: 4,
  onboarding_hidden: true,
  ui_theme: "dark",
  ui_language: "vi",
  role: "ADMIN",
  client_config: { tokens_per_char_milli: 1, tts_max_chars: 1000, tts_sync_char_cap: 500, terms_version: "v1" },
};

function renderLayout() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <I18nProvider>
          <AdminLayout>
            <div>admin content</div>
          </AdminLayout>
        </I18nProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

describe("AdminLayout guard", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    replaceMock.mockReset();
  });

  it("redirects a plain USER away to /studio/", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.resolve({ ...ADMIN_PROFILE, role: "USER" });
      return Promise.resolve({});
    });
    renderLayout();
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/studio/"));
    expect(screen.queryByText("admin content")).not.toBeInTheDocument();
  });

  it("redirects to /login/ on a 401", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new ApiError(401, "UNAUTHORIZED", "sign in required"));
      return Promise.resolve({});
    });
    renderLayout();
    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/login/"));
  });

  it("renders admin content for an ADMIN profile without redirecting", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.resolve(ADMIN_PROFILE);
      return Promise.resolve({});
    });
    renderLayout();
    await screen.findByText("admin content");
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
