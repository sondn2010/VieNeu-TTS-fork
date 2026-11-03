/** TC-01: the accept button is disabled until the checkbox is checked;
 * Escape and a backdrop click do nothing; accepting posts the terms
 * version and stores the `localStorage` flag. */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../lib/i18n/i18n-provider";
import { TERMS_ACCEPTED_STORAGE_KEY, TermsConsentModal } from "./terms-consent-modal";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

function stubProfileFetch() {
  apiFetchMock.mockImplementation((path: string) => {
    if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
    return Promise.resolve({ status: "ok" });
  });
}

function renderModal(onAccepted = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <TermsConsentModal termsVersion="1.0" onAccepted={onAccepted} />
      </I18nProvider>
    </QueryClientProvider>,
  );
  return { onAccepted };
}

describe("TermsConsentModal", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    stubProfileFetch();
    window.localStorage.clear();
  });

  it("disables the accept button until the checkbox is checked", () => {
    renderModal();
    const button = screen.getByRole("button", { name: "Đồng ý và tiếp tục" });
    expect(button).toBeDisabled();

    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeEnabled();

    fireEvent.click(screen.getByRole("checkbox"));
    expect(button).toBeDisabled();
  });

  it("does nothing on Escape", () => {
    const { onAccepted } = renderModal();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(onAccepted).not.toHaveBeenCalled();
  });

  it("does nothing on a backdrop click", () => {
    const { onAccepted } = renderModal();
    fireEvent.click(screen.getByRole("presentation"));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(onAccepted).not.toHaveBeenCalled();
  });

  it("posts the terms version and stores the localStorage flag on accept", async () => {
    const { onAccepted } = renderModal();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Đồng ý và tiếp tục" }));

    await waitFor(() => expect(onAccepted).toHaveBeenCalledTimes(1));
    expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/user/terms/accept", {
      method: "POST",
      body: { terms_version: "1.0" },
    });
    expect(window.localStorage.getItem(TERMS_ACCEPTED_STORAGE_KEY)).toBe("true");
  });

  it("keeps the modal open and shows an error when accept fails", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
      if (path === "/api/v1/user/terms/accept") return Promise.reject(new Error("server error"));
      return Promise.resolve({});
    });
    const { onAccepted } = renderModal();
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Đồng ý và tiếp tục" }));

    await waitFor(() => expect(screen.getByText("Không thể lưu. Vui lòng thử lại.")).toBeInTheDocument());
    expect(onAccepted).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
