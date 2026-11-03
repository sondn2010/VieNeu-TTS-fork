/** Shared `I18nProvider` + `QueryClientProvider` test wrapper. `I18nProvider`
 * itself calls the (mocked) `apiFetch` once on mount for the profile query —
 * callers that don't care about that call can use `stubProfileFetchReject`
 * to give it an isolated, harmless rejection. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import type { Mock } from "vitest";

import { I18nProvider } from "../lib/i18n/i18n-provider";

export function renderWithProviders(element: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider>{element}</I18nProvider>
    </QueryClientProvider>,
  );
}

export function stubProfileFetchReject(apiFetchMock: Mock, otherPaths: Record<string, unknown> = {}): void {
  apiFetchMock.mockImplementation((path: string) => {
    if (path === "/api/v1/user/profile") {
      return Promise.reject(new Error("no profile in this test"));
    }
    if (path in otherPaths) {
      return Promise.resolve(otherPaths[path]);
    }
    return Promise.resolve({});
  });
}
