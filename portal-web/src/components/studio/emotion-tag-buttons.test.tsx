import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders, stubProfileFetchReject } from "../../test-support/render-with-providers";
import { EmotionTagButtons } from "./emotion-tag-buttons";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

describe("EmotionTagButtons", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    stubProfileFetchReject(apiFetchMock);
  });

  it("inserts the [cười] tag", async () => {
    const onInsert = vi.fn();
    renderWithProviders(<EmotionTagButtons onInsert={onInsert} />);
    await userEvent.click(screen.getByText("Cười"));
    expect(onInsert).toHaveBeenCalledWith("[cười] ");
  });

  it("inserts the [thở dài] tag", async () => {
    const onInsert = vi.fn();
    renderWithProviders(<EmotionTagButtons onInsert={onInsert} />);
    await userEvent.click(screen.getByText("Thở dài"));
    expect(onInsert).toHaveBeenCalledWith("[thở dài] ");
  });

  it("inserts the [hắng giọng] tag", async () => {
    const onInsert = vi.fn();
    renderWithProviders(<EmotionTagButtons onInsert={onInsert} />);
    await userEvent.click(screen.getByText("Hắng giọng"));
    expect(onInsert).toHaveBeenCalledWith("[hắng giọng] ");
  });
});
