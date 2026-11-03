import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, resetCsrfTokenCacheForTests } from "./api-client-with-csrf";
import { ApiError } from "./api-error";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** `noUncheckedIndexedAccess` makes `mock.calls[i]` possibly `undefined`;
 * every call site here already asserted the call count first. */
function callArgs(mock: ReturnType<typeof vi.fn>, index: number): [string, RequestInit & { headers: Record<string, string> }] {
  const call = mock.mock.calls[index];
  if (!call) throw new Error(`expected a call at index ${index}`);
  return call as [string, RequestInit & { headers: Record<string, string> }];
}

describe("apiFetch", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    resetCsrfTokenCacheForTests();
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("adds X-CSRF-Token to a mutating request after fetching it once", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "tok-1" }))
      .mockResolvedValueOnce(jsonResponse(200, { status: "ok" }));

    await apiFetch("/api/v1/user/password", { method: "POST", body: { a: 1 } });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(callArgs(fetchMock, 0)[0]).toBe("/api/v1/auth/csrf");
    const [url, options] = callArgs(fetchMock, 1);
    expect(url).toBe("/api/v1/user/password");
    expect(options.headers["X-CSRF-Token"]).toBe("tok-1");
    expect(options.credentials).toBe("same-origin");
    expect(JSON.parse(options.body as string)).toEqual({ a: 1 });
  });

  it("never fetches a CSRF token for a GET request", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, { ok: true }));

    await apiFetch("/api/v1/user/profile");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(callArgs(fetchMock, 0)[0]).toBe("/api/v1/user/profile");
  });

  it("parses the error envelope into a typed ApiError", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(422, { error: { code: "VALIDATION_ERROR", message: "bad input", index: 2 } }),
    );

    let caught: unknown;
    try {
      await apiFetch("/api/v1/user/profile");
    } catch (err) {
      caught = err;
    }
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({ status: 422, code: "VALIDATION_ERROR", message: "bad input", extra: { index: 2 } });
  });

  it("retries once with a fresh CSRF token on a stale-token 403", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "stale" }))
      .mockResolvedValueOnce(jsonResponse(403, { error: { code: "CSRF_FAILED", message: "bad token" } }))
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "fresh" }))
      .mockResolvedValueOnce(jsonResponse(200, { status: "ok" }));

    const result = await apiFetch("/api/v1/user/password", { method: "POST", body: {} });

    expect(result).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledTimes(4);
    const retryOptions = callArgs(fetchMock, 3)[1];
    expect(retryOptions.headers["X-CSRF-Token"]).toBe("fresh");
  });

  it("returns undefined for a 204 response", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(200, { csrf_token: "tok-1" }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiFetch("/api/v1/tts/recordings/abc", { method: "DELETE" })).resolves.toBeUndefined();
  });
});
