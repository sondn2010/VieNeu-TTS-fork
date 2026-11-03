import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../../lib/i18n/i18n-provider";
import { TokenBalanceWidget } from "./token-balance-widget";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider>{ui}</I18nProvider>
    </QueryClientProvider>,
  );
}

describe("TokenBalanceWidget", () => {
  it("formats the balance with vi-VN thousands separators", () => {
    renderWithProviders(<TokenBalanceWidget balance={140574} quota={150000} />);
    expect(screen.getByText("140.574 / 150.000")).toBeInTheDocument();
  });

  it("formats zero without a leftover decimal or grouping artifact", () => {
    renderWithProviders(<TokenBalanceWidget balance={0} quota={150000} />);
    expect(screen.getByText("0 / 150.000")).toBeInTheDocument();
  });
});
