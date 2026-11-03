"use client";

import { useState, type FormEvent } from "react";

import { useI18n } from "../../lib/i18n/i18n-provider";
import { getAdminMessages } from "../../lib/i18n/messages-admin-en";
import { useUpdatePlanMutation, type AdminUserRow } from "./admin-api-hooks";

export interface PlanEditFormProps {
  user: AdminUserRow;
}

function toDateInputValue(iso: string | null): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

export function PlanEditForm({ user }: PlanEditFormProps) {
  const { language } = useI18n();
  const t = getAdminMessages(language);
  const [planTier, setPlanTier] = useState(user.plan_tier);
  const [quotaTotal, setQuotaTotal] = useState(String(user.token_quota_total));
  const [dailyLimit, setDailyLimit] = useState(String(user.daily_char_limit));
  const [expiry, setExpiry] = useState(toDateInputValue(user.plan_expires_at));
  const [resetDaily, setResetDaily] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mutation = useUpdatePlanMutation(user.id);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await mutation.mutateAsync({
        plan_tier: planTier || undefined,
        token_quota_total: quotaTotal ? Number(quotaTotal) : undefined,
        daily_char_limit: dailyLimit ? Number(dailyLimit) : undefined,
        plan_expires_at: expiry ? new Date(`${expiry}T00:00:00Z`).toISOString() : undefined,
        reset_daily_remaining: resetDaily,
      });
      setResetDaily(false);
    } catch {
      setError(t.guard.genericError);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
        {t.userDetail.planTierLabel}
        <input type="text" value={planTier} onChange={(e) => setPlanTier(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
        {t.userDetail.planQuotaTotalLabel}
        <input type="number" value={quotaTotal} onChange={(e) => setQuotaTotal(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
        {t.userDetail.planDailyLimitLabel}
        <input type="number" value={dailyLimit} onChange={(e) => setDailyLimit(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
        {t.userDetail.planExpiryLabel}
        <input type="date" value={expiry} onChange={(e) => setExpiry(e.target.value)} style={{ width: "100%", padding: 8, marginTop: 4 }} />
      </label>
      <label style={{ fontSize: 12, color: "var(--color-text-secondary)", display: "flex", alignItems: "center", gap: 6 }}>
        <input type="checkbox" checked={resetDaily} onChange={(e) => setResetDaily(e.target.checked)} />
        {t.userDetail.planResetDailyLabel}
      </label>
      {error && <p style={{ color: "var(--color-danger-text)", fontSize: 12, margin: 0 }}>{error}</p>}
      <button
        type="submit"
        disabled={mutation.isPending}
        style={{ background: "var(--color-accent)", color: "#fff", border: "none", borderRadius: 6, padding: "6px 12px", alignSelf: "flex-start" }}
      >
        {t.userDetail.planSaveButton}
      </button>
    </form>
  );
}
