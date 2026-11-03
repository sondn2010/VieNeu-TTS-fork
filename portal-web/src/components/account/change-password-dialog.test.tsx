import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../lib/api/api-error";
import { I18nProvider } from "../../lib/i18n/i18n-provider";
import { ChangePasswordDialog } from "./change-password-dialog";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

// `I18nProvider` itself calls `apiFetch` once on mount (the profile query),
// through the same mocked module — give that call its own stub so each
// test's own mock setup for `/api/v1/user/password` is unambiguous.
function stubProfileFetch() {
  apiFetchMock.mockImplementation((path: string) => {
    if (path === "/api/v1/user/profile") {
      return Promise.reject(new Error("no profile in this test"));
    }
    return Promise.resolve({});
  });
}

function renderDialog() {
  const onClose = vi.fn();
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <ChangePasswordDialog onClose={onClose} />
      </I18nProvider>
    </QueryClientProvider>,
  );
  return { onClose };
}

function fillForm(current: string, next: string, confirm: string) {
  fireEvent.change(screen.getByLabelText(/mật khẩu hiện tại/i), { target: { value: current } });
  fireEvent.change(screen.getByLabelText(/^mật khẩu mới/i), { target: { value: next } });
  fireEvent.change(screen.getByLabelText(/nhập lại mật khẩu mới/i), { target: { value: confirm } });
}

function passwordChangeCalls() {
  return apiFetchMock.mock.calls.filter(([path]) => path === "/api/v1/user/password");
}

describe("ChangePasswordDialog", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    stubProfileFetch();
  });

  it("shows a mismatch error and never calls the password API when new passwords differ", () => {
    renderDialog();
    fillForm("current-pw", "a-new-password-1", "a-new-password-2");
    fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));

    expect(screen.getByText("Hai mật khẩu mới không khớp.")).toBeInTheDocument();
    expect(passwordChangeCalls()).toHaveLength(0);
  });

  it("shows a too-short error and never calls the password API for a short new password", () => {
    renderDialog();
    fillForm("current-pw", "short", "short");
    fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));

    expect(screen.getByText("Mật khẩu mới phải có ít nhất 10 ký tự.")).toBeInTheDocument();
    expect(passwordChangeCalls()).toHaveLength(0);
  });

  it("shows the wrong-current-password error from the API", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
      if (path === "/api/v1/user/password") {
        return Promise.reject(new ApiError(401, "INVALID_CREDENTIALS", "current password is incorrect"));
      }
      return Promise.reject(new Error(`unexpected path: ${path}`));
    });
    renderDialog();
    fillForm("wrong-current", "a-valid-new-password", "a-valid-new-password");
    fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));

    await waitFor(() => expect(screen.getByText("Mật khẩu hiện tại không đúng.")).toBeInTheDocument());
    expect(passwordChangeCalls()).toEqual([
      ["/api/v1/user/password", { method: "POST", body: { current_password: "wrong-current", new_password: "a-valid-new-password" } }],
    ]);
  });

  it("shows a success message when the API accepts the change", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
      if (path === "/api/v1/user/password") return Promise.resolve({ status: "ok" });
      return Promise.reject(new Error(`unexpected path: ${path}`));
    });
    renderDialog();
    fillForm("current-pw", "a-valid-new-password", "a-valid-new-password");
    fireEvent.click(screen.getByRole("button", { name: "Đổi mật khẩu" }));

    await waitFor(() => expect(screen.getByText("Đã đổi mật khẩu thành công.")).toBeInTheDocument());
  });
});
