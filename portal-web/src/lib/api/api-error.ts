/** The portal's JSON error envelope (`{"error": {"code", "message", ...}}`),
 * parsed into a typed exception so callers can branch on `code` without
 * re-parsing the response body. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly extra: Readonly<Record<string, unknown>>;

  constructor(status: number, code: string, message: string, extra: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.extra = extra;
  }
}
