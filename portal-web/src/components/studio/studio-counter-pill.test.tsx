import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders, stubProfileFetchReject } from "../../test-support/render-with-providers";
import { StudioCounterPill } from "./studio-counter-pill";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

describe("StudioCounterPill", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    stubProfileFetchReject(apiFetchMock);
  });

  it("renders the spec format with Vietnamese thousands separators", () => {
    renderWithProviders(<StudioCounterPill charCount={0} tokens={0} remainingChars={50000} overBudget={false} />);
    expect(screen.getByRole("status").textContent).toBe("0 ký tự · ~0 token · còn 50.000");
  });

  it("is not styled as a warning under the limit", () => {
    renderWithProviders(<StudioCounterPill charCount={120} tokens={5} remainingChars={49880} overBudget={false} />);
    const pill = screen.getByRole("status");
    expect(pill).not.toHaveStyle({ color: "var(--color-danger-text)" });
  });

  it("styles as a warning when over budget", () => {
    renderWithProviders(<StudioCounterPill charCount={60000} tokens={3000} remainingChars={50000} overBudget />);
    const pill = screen.getByRole("status");
    expect(pill).toHaveStyle({ color: "var(--color-danger-text)" });
  });
});
