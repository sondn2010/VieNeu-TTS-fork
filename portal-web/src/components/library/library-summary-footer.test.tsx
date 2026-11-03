import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders, stubProfileFetchReject } from "../../test-support/render-with-providers";
import { LibrarySummaryFooter } from "./library-summary-footer";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

describe("LibrarySummaryFooter", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    stubProfileFetchReject(apiFetchMock);
  });

  it("renders the TC-07 spec example verbatim", () => {
    renderWithProviders(<LibrarySummaryFooter shownCount={2} totalCount={2} totalDurationSeconds={293.3} />);
    expect(screen.getByText("2 trong số 2 giọng nói")).toBeInTheDocument();
    expect(screen.getByText("Tổng thời lượng: 293.3s")).toBeInTheDocument();
  });

  it("reflects a filtered subset of the total", () => {
    renderWithProviders(<LibrarySummaryFooter shownCount={1} totalCount={3} totalDurationSeconds={146.0} />);
    expect(screen.getByText("1 trong số 3 giọng nói")).toBeInTheDocument();
    expect(screen.getByText("Tổng thời lượng: 146.0s")).toBeInTheDocument();
  });
});
