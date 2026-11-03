"use client";

import { formatVietnameseNumber } from "../../lib/format/vietnamese-number-and-date-format";
import { useI18n } from "../../lib/i18n/i18n-provider";

export interface StudioCounterPillProps {
  charCount: number;
  tokens: number;
  remainingChars: number;
  overBudget: boolean;
}

export function StudioCounterPill({ charCount, tokens, remainingChars, overBudget }: StudioCounterPillProps) {
  const { messages } = useI18n();
  const t = messages.studio;

  return (
    <div
      role="status"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: 12,
        padding: "6px 10px",
        borderRadius: 8,
        background: "#14141d",
        color: overBudget ? "var(--color-danger-text)" : "var(--color-text-secondary)",
      }}
    >
      {charCount} {t.counterCharsSuffix} · {t.counterTokensPrefix}
      {tokens} {t.counterTokensSuffix} · {t.counterRemainingPrefix} {formatVietnameseNumber(remainingChars)}
    </div>
  );
}
