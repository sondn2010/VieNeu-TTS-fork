"use client";

import { CheckSquare, ChevronDown } from "lucide-react";

import { useI18n } from "../../lib/i18n/i18n-provider";

export interface OnboardingProgressBarProps {
  completedSteps: number;
  onHide: () => void;
}

/** The expand arrow is permanently disabled in C1 — the plan leaves the
 * individual onboarding steps undefined, so there is nothing to expand
 * into yet. */
export function OnboardingProgressBar({ completedSteps, onHide }: OnboardingProgressBarProps) {
  const { messages } = useI18n();
  const t = messages.studio;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: 8,
        padding: "8px 14px",
        marginBottom: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: "var(--color-text-primary)" }}>
        <CheckSquare size={16} aria-hidden color="var(--color-accent)" />
        <span style={{ fontWeight: 600 }}>{t.onboardingStart}</span>
        <span
          style={{
            background: "rgba(124,92,252,0.15)",
            color: "var(--color-accent)",
            borderRadius: 999,
            padding: "2px 8px",
            fontSize: 11,
          }}
        >
          {t.onboardingDonePrefix} {completedSteps}/4
        </span>
        <button
          type="button"
          disabled
          title={messages.common.comingSoon}
          aria-label={messages.common.comingSoon}
          style={{ background: "none", border: "none", color: "var(--color-text-muted)", cursor: "not-allowed" }}
        >
          <ChevronDown size={14} aria-hidden />
        </button>
      </div>
      <button
        type="button"
        onClick={onHide}
        style={{ background: "none", border: "none", color: "var(--color-text-secondary)", cursor: "pointer", fontSize: 12 }}
      >
        {t.onboardingHide}
      </button>
    </div>
  );
}
