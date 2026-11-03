import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test-support/render-with-providers";
import { ApiError } from "../../lib/api/api-error";
import { SystemDictionaryRulesEditor } from "./system-dictionary-rules-editor";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

const RULES_RESPONSE = {
  items: [
    {
      id: "r1",
      source_term: "km/h",
      phonetic_replacement: "ki lô mét trên giờ",
      match_whole_word: true,
      case_sensitive: false,
      is_enabled: true,
      sort_order: 0,
      note: "",
      rule_kind: "REPLACE",
    },
  ],
  total_count: 1,
  etag: "etag-1",
};

describe("SystemDictionaryRulesEditor", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it("shows the etag conflict message when saving races a newer edit", async () => {
    apiFetchMock.mockImplementation((path: string, options?: { method?: string }) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
      if (path.endsWith("/rules?limit=200")) return Promise.resolve(RULES_RESPONSE);
      if (path.endsWith("/rules") && options?.method === "PUT") {
        return Promise.reject(new ApiError(409, "ETAG_MISMATCH", "stale"));
      }
      return Promise.resolve({});
    });
    renderWithProviders(<SystemDictionaryRulesEditor dictionaryId={1} />);

    await screen.findByDisplayValue("km/h");
    fireEvent.click(screen.getByText("Lưu toàn bộ"));

    await waitFor(() =>
      expect(
        screen.getByText("Bộ từ điển đã thay đổi từ nơi khác. Vui lòng tải lại trang và thử lại."),
      ).toBeInTheDocument(),
    );
  });

  it("the in-browser preview applies an enabled REPLACE rule", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path === "/api/v1/user/profile") return Promise.reject(new Error("no profile in this test"));
      if (path.endsWith("/rules?limit=200")) return Promise.resolve(RULES_RESPONSE);
      return Promise.resolve({});
    });
    renderWithProviders(<SystemDictionaryRulesEditor dictionaryId={1} />);
    await screen.findByDisplayValue("km/h");

    fireEvent.change(screen.getByPlaceholderText("Nhập văn bản để xem thử cách áp dụng quy tắc..."), {
      target: { value: "Tốc độ 5 km/h" },
    });
    await waitFor(() => expect(screen.getByText("Tốc độ 5 ki lô mét trên giờ")).toBeInTheDocument());
  });
});
