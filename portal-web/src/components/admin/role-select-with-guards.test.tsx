import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test-support/render-with-providers";
import { RoleSelectWithGuards } from "./role-select-with-guards";
import type { AdminUserRow } from "./admin-api-hooks";

const apiFetchMock = vi.fn();

vi.mock("../../lib/api/api-client-with-csrf", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

function stubProfile(profile: Record<string, unknown>) {
  apiFetchMock.mockImplementation((path: string) => {
    if (path === "/api/v1/user/profile") return Promise.resolve(profile);
    return Promise.resolve({});
  });
}

const TARGET_OTHER = { id: "target-1", email: "target@example.com", role: "USER" } as unknown as AdminUserRow;
const TARGET_SELF = { id: "actor-1", email: "actor@example.com", role: "SUPERADMIN" } as unknown as AdminUserRow;

describe("RoleSelectWithGuards", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it("is hidden for a plain ADMIN actor", async () => {
    stubProfile({ id: "actor-1", role: "ADMIN" });
    renderWithProviders(<RoleSelectWithGuards target={TARGET_OTHER} onChange={vi.fn()} />);
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith("/api/v1/user/profile"));
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("is enabled for a SUPERADMIN acting on another account", async () => {
    stubProfile({ id: "actor-1", role: "SUPERADMIN" });
    renderWithProviders(<RoleSelectWithGuards target={TARGET_OTHER} onChange={vi.fn()} />);
    const select = await screen.findByRole("combobox");
    expect(select).not.toBeDisabled();
  });

  it("is disabled when the target is the actor's own account", async () => {
    stubProfile({ id: "actor-1", role: "SUPERADMIN" });
    renderWithProviders(<RoleSelectWithGuards target={TARGET_SELF} onChange={vi.fn()} />);
    const select = await screen.findByRole("combobox");
    expect(select).toBeDisabled();
  });
});
