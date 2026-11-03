"use client";

import { useState, type FormEvent } from "react";

import { ApiError } from "../../lib/api/api-error";
import { formatVietnameseNumber } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useAdjustTokensMutation } from "./admin-api-hooks";

export interface TokenAdjustFormProps {
  userId: string;
}

export function TokenAdjustForm({ userId }: TokenAdjustFormProps) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [resultingBalance, setResultingBalance] = useState<number | null>(null);
  const mutation = useAdjustTokensMutation(userId);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const parsed = Number(delta);
    if (!Number.isFinite(parsed) || parsed === 0 || !reason.trim()) {
      setError(t.guard.genericError);
      return;
    }
    try {
      const result = await mutation.mutateAsync({ delta: parsed, reason });
      setResultingBalance(result.token_balance);
      setDelta("");
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.guard.genericError);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
        {t.userDetail.tokenDeltaLabel}
        <input type="number" value={delta} onChange={(e) => setDelta(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
        {t.userDetail.tokenReasonLabel}
        <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
      </label>
      {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
      {resultingBalance !== null && (
        <p style={{ color: "var(--color-success-text)", fontSize: 12, margin: 0 }}>
          {t.userDetail.resultingBalance}: {formatVietnameseNumber(resultingBalance)}
        </p>
      )}
      <button
        type="submit"
        disabled={mutation.isPending}
        style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px", alignSelf: "flex-start" }}
      >
        {t.userDetail.tokenAdjustButton}
      </button>
    </form>
  );
}
