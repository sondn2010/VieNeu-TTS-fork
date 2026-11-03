import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders, stubProfileFetchReject } from "../../test-support/render-with-providers";
import { TokenAdjustForm } from "./token-adjust-form";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

function tokensCalls() {
  return apiFetchMock.mock.calls.filter(([path]) => typeof path === "string" && path.includes("/tokens"));
}

function fillForm(delta: string, reason: string) {
  fireEvent.change(screen.getByLabelText("Số token thay đổi (+/-)"), { target: { value: delta } });
  fireEvent.change(screen.getByLabelText("Lý do"), { target: { value: reason } });
}

describe("TokenAdjustForm", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    stubProfileFetchReject(apiFetchMock);
  });

  it("rejects a zero delta without calling the API", () => {
    renderWithProviders(<TokenAdjustForm userId="u1" />);
    fillForm("0", "some reason");
    fireEvent.click(screen.getByRole("button", { name: "Điều chỉnh" }));
    expect(tokensCalls()).toHaveLength(0);
  });

  it("rejects an empty reason without calling the API", () => {
    renderWithProviders(<TokenAdjustForm userId="u1" />);
    fillForm("100", "");
    fireEvent.click(screen.getByRole("button", { name: "Điều chỉnh" }));
    expect(tokensCalls()).toHaveLength(0);
  });

  it("adjusts tokens and shows the resulting balance on success", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
      if (path.includes("/tokens")) return Promise.resolve({ token_balance: 1234 });
      return Promise.resolve({});
    });
    renderWithProviders(<TokenAdjustForm userId="u1" />);
    fillForm("100", "goodwill credit");
    fireEvent.click(screen.getByRole("button", { name: "Điều chỉnh" }));

    await waitFor(() => expect(tokensCalls()).toHaveLength(1));
    expect(tokensCalls()[0]).toEqual([
      "/api/v1/admin/users/u1/tokens",
      { method: "POST", body: { delta: 100, reason: "goodwill credit" } },
    ]);
    await waitFor(() => expect(screen.getByText(/1\.234/)).toBeInTheDocument());
  });
});
